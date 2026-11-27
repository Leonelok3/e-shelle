import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessProfile

from .inbox import _save_inbound
from .models import BusinessWhatsAppConnection, BusinessWhatsAppReplyJob
from .onboarding import MetaOnboardingError
from .reply_jobs import dispatch_pending_jobs, process_reply_job

Status = BusinessWhatsAppReplyJob.Status


@override_settings(WHATSAPP_COMMERCE_AI_ENABLED=True)
class BusinessWhatsAppReplyQueueTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="reply-queue-owner")
        self.business = BusinessProfile.objects.create(
            owner=self.owner, module=BusinessProfile.Module.RESTO, name="Test de file",
            plan=BusinessProfile.Plan.BUSINESS, activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=1), ai_credits=20,
        )
        self.connection = BusinessWhatsAppConnection.objects.create(
            business=self.business, waba_id="queue-waba", phone_number_id="queue-phone",
            status=BusinessWhatsAppConnection.Status.ACTIVE, agent_enabled=True,
        )
        self.connection.set_access_token("test-token")
        self.connection.save(update_fields=["access_token_encrypted"])

    def receive(self, message_id, *, body="Bonjour"):
        return _save_inbound(
            self.connection,
            {"from": "237699123456", "id": message_id, "type": "text", "text": {"body": body}},
            "", timezone.now(),
        )

    def test_duplicate_webhook_and_failed_publication_keep_one_pending_job(self):
        _, inbound, created = self.receive("queue-publish")
        self.assertTrue(created)
        _, duplicate, created = self.receive("queue-publish")
        self.assertFalse(created)
        self.assertEqual(duplicate.pk, inbound.pk)
        job = inbound.reply_job
        publish = Mock(side_effect=OSError("broker indisponible"))
        self.assertEqual(dispatch_pending_jobs(publish), 0)
        self.assertEqual(BusinessWhatsAppReplyJob.objects.count(), 1)
        job.refresh_from_db()
        self.assertEqual(job.status, Status.PENDING)
        publish.side_effect = None
        publish.reset_mock()
        self.assertEqual(dispatch_pending_jobs(publish), 0)
        publish.assert_not_called()
        BusinessWhatsAppReplyJob.objects.filter(pk=job.pk).update(dispatch_after=timezone.now() - timedelta(seconds=1))
        self.assertEqual(dispatch_pending_jobs(publish), 1)
        publish.assert_called_once_with(job.pk)

    @patch("whatsapp_commerce.reply_jobs._respond", return_value=Status.SENT)
    def test_message_order_is_preserved_per_contact(self, respond):
        _, first, _ = self.receive("queue-first")
        _, second, _ = self.receive("queue-second")
        publish = Mock()
        self.assertEqual(dispatch_pending_jobs(publish), 1)
        publish.assert_called_once_with(first.reply_job.pk)
        self.assertFalse(process_reply_job(second.reply_job.pk))
        respond.assert_not_called()
        self.assertTrue(process_reply_job(first.reply_job.pk))
        self.assertTrue(process_reply_job(second.reply_job.pk))

    @patch("whatsapp_commerce.inbox._request_meta", side_effect=MetaOnboardingError("Délai Meta dépassé"))
    @patch("whatsapp_commerce.brain.call_llm")
    def test_uncertain_send_goes_to_review_without_replaying_or_recharging(self, llm, meta):
        llm.return_value = json.dumps({
            "intention": "qualification", "reponse": "Quel plat souhaites-tu ?", "action_next": "qualifier",
        })
        contact, inbound, _ = self.receive("queue-meta-timeout")
        job = inbound.reply_job
        self.assertTrue(process_reply_job(job.pk))
        self.assertFalse(process_reply_job(job.pk))
        job.refresh_from_db()
        contact.refresh_from_db()
        self.business.refresh_from_db()
        self.assertEqual(job.status, Status.REVIEW)
        self.assertTrue(contact.agent_paused)
        self.assertEqual(self.business.ai_credits, 19)
        meta.assert_called_once()

    @patch("whatsapp_commerce.reply_jobs._respond")
    def test_stalled_job_is_paused_and_owner_can_resume_for_new_messages(self, respond):
        contact, inbound, _ = self.receive("queue-stalled")
        _, waiting, _ = self.receive("queue-waiting")
        job = inbound.reply_job
        BusinessWhatsAppReplyJob.objects.filter(pk=job.pk).update(
            status=Status.PROCESSING, updated_at=timezone.now() - timedelta(minutes=10),
        )
        publish = Mock()
        self.assertEqual(dispatch_pending_jobs(publish), 0)
        publish.assert_not_called()
        self.assertFalse(process_reply_job(job.pk))
        job.refresh_from_db()
        waiting.reply_job.refresh_from_db()
        contact.refresh_from_db()
        self.assertEqual(job.status, Status.REVIEW)
        self.assertEqual(waiting.reply_job.status, Status.SKIPPED)
        self.assertTrue(contact.agent_paused)
        respond.assert_not_called()

        self.client.force_login(self.owner)
        url = reverse("whatsapp_commerce:business_contact_reply", args=[self.business.pk, contact.pk])
        self.assertEqual(self.client.post(url, {"agent_mode": "resume"}).status_code, 302)
        _, resumed, _ = self.receive("queue-resumed")
        self.assertEqual(resumed.reply_job.status, Status.PENDING)
        self.assertEqual(self.client.post(url, {"agent_mode": "pause"}).status_code, 302)
        resumed.reply_job.refresh_from_db()
        self.assertEqual(resumed.reply_job.status, Status.SKIPPED)
        _, manual, _ = self.receive("queue-manual")
        self.assertFalse(BusinessWhatsAppReplyJob.objects.filter(message=manual).exists())
