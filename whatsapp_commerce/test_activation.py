import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile

from .activation import test_body as activation_message
from .models import (
    BusinessWhatsAppActivation,
    BusinessWhatsAppConnection,
    BusinessWhatsAppMessage,
    BusinessWhatsAppReplyJob,
)
from .reply_jobs import process_reply_job


@override_settings(WHATSAPP_COMMERCE_AI_ENABLED=True, WHATSAPP_APP_SECRET="activation-test-secret")
class GuidedAgentActivationTests(TestCase):
    def setUp(self):
        owner = get_user_model().objects.create_user(username="activation-owner")
        self.business = BusinessProfile.objects.create(
            owner=owner, name="Chez E-Shelle", module=BusinessProfile.Module.RESTO,
            plan=BusinessProfile.Plan.BUSINESS, activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=1), ai_credits=20,
        )
        self.connection = BusinessWhatsAppConnection.objects.create(
            business=self.business, waba_id="guided-waba", phone_number_id="guided-phone",
            status=BusinessWhatsAppConnection.Status.ACTIVE, display_phone_number="+237699000054",
            phone_registered=True, webhook_subscribed=True,
        )
        self.connection.set_access_token("test-token")
        self.connection.save(update_fields=["access_token_encrypted"])
        self.dashboard = reverse("whatsapp_commerce:business_dashboard", args=[self.business.pk])
        self.configure = reverse("whatsapp_commerce:business_agent_configure", args=[self.business.pk])
        self.client.force_login(owner)

    def webhook(self, *, inbound=(), statuses=()):
        value = {"metadata": {"phone_number_id": self.connection.phone_number_id},
                 "messages": list(inbound), "statuses": list(statuses)}
        body = json.dumps({"object": "whatsapp_business_account", "entry": [{
            "id": self.connection.waba_id, "changes": [{"field": "messages", "value": value}],
        }]})
        signature = "sha256=" + hmac.new(b"activation-test-secret", body.encode(), hashlib.sha256).hexdigest()
        response = self.client.post("/whatsapp/webhook/", body, content_type="application/json",
                                    HTTP_X_HUB_SIGNATURE_256=signature)
        self.assertEqual(response.status_code, 200)

    def inbound(self, body, *, sender="237699000052", message_id="activation-inbound"):
        self.webhook(inbound=[{
            "from": sender, "id": message_id, "timestamp": str(int(timezone.now().timestamp())),
            "type": "text", "text": {"body": body},
        }])

    def prepare(self):
        self.client.post(self.configure, {"action": "settings", "answer_hours": "on", "opening_hours": "Lundi, 11 h–22 h"})
        self.client.post(self.configure, {"action": "start_test", "test_sender": "+237699000052"})
        return BusinessWhatsAppActivation.objects.get(connection=self.connection)

    @patch("whatsapp_commerce.brain.call_llm")
    @patch("whatsapp_commerce.inbox._request_meta")
    def test_test_is_bound_to_sender_and_activation_waits_for_receipt(self, meta, llm):
        meta.return_value = {"messages": [{"id": "activation-outbound"}]}
        activation = self.prepare()
        body = activation_message(activation)
        self.assertContains(self.client.get(self.dashboard), body)
        self.inbound(body, sender="237699000053", message_id="wrong-sender")
        self.assertFalse(BusinessWhatsAppMessage.objects.exists())
        self.inbound(body)
        self.inbound(body)
        meta.assert_not_called()
        job = BusinessWhatsAppReplyJob.objects.get()
        self.assertTrue(job.message.is_activation_test)
        self.assertTrue(process_reply_job(job.pk))
        self.assertFalse(process_reply_job(job.pk))
        self.assertEqual(meta.call_args.kwargs["payload"]["to"], "237699000052")
        self.assertIn("Lundi, 11 h–22 h", meta.call_args.kwargs["payload"]["text"]["body"])
        llm.assert_not_called()
        self.business.refresh_from_db()
        self.assertEqual(self.business.ai_credits, 20)
        self.client.post(self.configure, {"action": "enable"})
        self.connection.refresh_from_db()
        self.assertFalse(self.connection.agent_enabled)
        self.webhook(statuses=[{"id": "activation-outbound", "status": "delivered"}])
        self.webhook(statuses=[{"id": "activation-outbound", "status": "sent"}])
        self.assertContains(self.client.get(self.dashboard), "Livraison confirmée par Meta.")
        self.inbound("Quels sont vos horaires ?", sender="237699000053", message_id="before-activation")
        self.client.post(self.configure, {"action": "enable"})
        self.connection.refresh_from_db()
        self.assertTrue(self.connection.agent_enabled)
        early_job = BusinessWhatsAppReplyJob.objects.get(message__wa_message_id="before-activation")
        process_reply_job(early_job.pk)
        early_job.refresh_from_db()
        self.assertEqual(early_job.status, BusinessWhatsAppReplyJob.Status.SKIPPED)
        meta.assert_called_once()

    @patch("whatsapp_commerce.inbox._request_meta")
    def test_attempts_cannot_enable_after_failure_or_changed_settings(self, meta):
        meta.return_value = {"messages": [{"id": "activation-failed-outbound"}]}
        activation = self.prepare()
        self.inbound(activation_message(activation))
        process_reply_job(BusinessWhatsAppReplyJob.objects.get().pk)
        self.webhook(statuses=[{"id": "activation-failed-outbound", "status": "failed"}])
        self.client.post(self.configure, {"action": "enable", "received_on_phone": "on"})
        self.connection.refresh_from_db()
        self.assertFalse(self.connection.agent_enabled)
        self.client.post(self.configure, {"action": "settings", "answer_hours": "on", "opening_hours": "Lundi, 9 h–18 h"})
        activation.refresh_from_db()
        self.assertIsNone(activation.test_reply_id)
        self.assertIsNone(activation.test_message_id)

    @patch("whatsapp_commerce.inbox._request_meta")
    def test_customer_scope_catalog_and_handoff(self, meta):
        meta.return_value = {"messages": [{"id": "activation-catalog-outbound"}]}
        item = BusinessCatalogItem.objects.create(business=self.business, title="Poulet braisé", price_label="4500 XAF")
        self.client.post(self.configure, {
            "action": "settings", "answer_catalog": "on", "agent_catalog_items": [item.pk],
        })
        self.connection.agent_enabled = True
        self.connection.save(update_fields=["agent_enabled"])
        self.inbound("Est-ce que je peux voir le menu ?", message_id="catalogue-client")
        job = BusinessWhatsAppReplyJob.objects.get(message__wa_message_id="catalogue-client")
        self.assertTrue(process_reply_job(job.pk))
        self.assertIn("Poulet braisé", meta.call_args.kwargs["payload"]["text"]["body"])
        self.inbound("Comment puis-je payer ?", message_id="paiement-client")
        job = BusinessWhatsAppReplyJob.objects.get(message__wa_message_id="paiement-client")
        self.assertTrue(process_reply_job(job.pk))
        job.refresh_from_db()
        self.assertEqual(job.status, BusinessWhatsAppReplyJob.Status.REVIEW)
        self.assertTrue(job.message.contact.agent_paused)
        meta.assert_called_once()

    def test_wrong_owner_and_incomplete_connection_cannot_start_test(self):
        self.connection.webhook_subscribed = False
        self.connection.save(update_fields=["webhook_subscribed"])
        activation = self.prepare()
        self.assertFalse(activation.test_code)
        self.assertContains(self.client.get(self.dashboard), "L’abonnement aux notifications de messages Meta est incomplet.")
        other = get_user_model().objects.create_user(username="activation-other-owner")
        self.client.force_login(other)
        self.assertEqual(self.client.post(self.configure, {"action": "enable"}).status_code, 404)
