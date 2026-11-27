from datetime import time, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile
from immobilier_cameroun.models import Bien, StatutBien
from payments.campay import reconcile_transaction
from salonhub.salons.models import OpeningHour, Salon, Service

from .inbox import _save_inbound
from .models import BusinessWhatsAppActivation, BusinessWhatsAppConnection, BusinessWhatsAppContact, BusinessWhatsAppReplyJob, WhatsAppDraftOrder
from .orchestrator import confirm_draft_order
from .reply_jobs import process_reply_job


@override_settings(WHATSAPP_COMMERCE_AI_ENABLED=True, CAMPAY_PUBLIC_BASE_URL="https://e-shelle.com")
class FollowUpTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="follow-up-owner")
        self.business = self.create_business("Agence Bonapriso", BusinessProfile.Module.IMMOBILIER)
        self.connection = BusinessWhatsAppConnection.objects.create(
            business=self.business, waba_id="follow-up-waba", phone_number_id="follow-up-number",
            status=BusinessWhatsAppConnection.Status.ACTIVE, agent_enabled=True,
        )
        self.connection.set_access_token("fake-test-token")
        self.connection.save(update_fields=["access_token_encrypted"])
        self.activation = BusinessWhatsAppActivation.objects.create(connection=self.connection, answer_hours=False)
        self.sender = "237699000065"
        self.counter = 0
        self.client.force_login(self.owner)

    def create_business(self, name, module):
        return BusinessProfile.objects.create(
            owner=self.owner, module=module, name=name, city="Douala",
            plan=BusinessProfile.Plan.BUSINESS, activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=7),
        )

    def listing(self, title):
        return Bien.objects.create(
            agence=self.business, proprietaire=self.owner, titre=title, ville="Douala", quartier="Bonapriso",
            prix=250000, statut=StatutBien.PUBLIE,
        )

    def send(self, text):
        self.counter += 1
        _, message, _ = _save_inbound(self.connection, {
            "from": self.sender, "id": f"follow-up-in-{self.counter}", "type": "text", "text": {"body": text},
        }, "Client test", timezone.now())
        with patch("whatsapp_commerce.inbox._request_meta", return_value={
            "messages": [{"id": f"follow-up-out-{self.counter}"}],
        }) as meta:
            self.assertTrue(process_reply_job(message.reply_job.pk))
        message.reply_job.refresh_from_db()
        return message.reply_job, meta.call_args.kwargs["payload"]["text"]["body"] if meta.called else ""

    def list_url(self):
        return reverse("whatsapp_commerce:follow_up_list", args=[self.business.pk])

    def cases(self, kind):
        response = self.client.get(self.list_url(), {"type": kind})
        self.assertContains(response, "À reprendre")
        return list(response.context["page"])

    def test_review_displays_latest_question_and_owner_can_close_it_without_changing_pause(self):
        listing = self.listing("Appartement Bonapriso")
        self.send(f"BIEN {listing.pk}")
        job, _ = self.send("Avez-vous le titre foncier ?")
        self.assertEqual(job.status, BusinessWhatsAppReplyJob.Status.REVIEW)
        [case] = self.cases("conversations")
        self.assertEqual(case.follow_up_property, listing)
        self.assertContains(self.client.get(self.list_url()), f"?contact={case.message.contact_id}#conversation")
        close_url = reverse("whatsapp_commerce:follow_up_close", args=[self.business.pk, "conversations", job.pk])
        other = self.create_business("Autre entreprise", BusinessProfile.Module.SERVICES)
        wrong_url = reverse("whatsapp_commerce:follow_up_close", args=[other.pk, "conversations", job.pk])
        self.assertEqual(self.client.post(wrong_url).status_code, 404)
        self.assertEqual(self.client.get(close_url).status_code, 405)
        self.assertEqual(self.client.post(close_url).status_code, 302)
        self.assertEqual(self.client.post(close_url).status_code, 302)
        self.assertEqual(self.cases("conversations"), [])
        self.assertTrue(BusinessWhatsAppContact.objects.get(pk=case.message.contact_id).agent_paused)

    def test_no_slots_creates_one_case_per_listing_and_confirmation_closes_the_correct_case(self):
        first = self.listing("Appartement A")
        second = self.listing("Appartement B")
        salon = Salon.objects.create(owner=self.owner, name="Agenda test", city="Douala", whatsapp_number=self.sender)
        service = Service.objects.create(salon=salon, name="Visite", price=0, duration_minutes=60)
        self.activation.booking_service = service
        self.activation.save(update_fields=["booking_service"])
        _, reply = self.send(f"Je souhaite visiter le BIEN {first.pk}")
        self.assertIn("Aucun créneau disponible", reply)
        _, reply = self.send("Aucun créneau ne me convient")
        self.assertIn("autre créneau", reply)
        self.send(f"Je souhaite visiter le BIEN {second.pk}")
        cases = self.cases("rendez-vous")
        self.assertEqual({case.follow_up_property_id for case in cases}, {first.pk, second.pk})
        self.assertEqual(len(cases), 2)
        self.assertFalse(cases[0].message.contact.agent_paused)
        day = timezone.localdate() + timedelta(days=1)
        OpeningHour.objects.create(salon=salon, weekday=day.weekday(), start_time=time(9), end_time=time(17))
        self.send(f"BIEN {first.pk}")
        _, reply = self.send(f"RDV {day} 09:00")
        self.assertIn("Visite confirmée", reply)
        self.assertEqual([case.follow_up_property_id for case in self.cases("rendez-vous")], [second.pk])

    def test_payment_queue_follows_verified_status_and_manual_close_is_not_payment(self):
        item = BusinessCatalogItem.objects.create(business=self.business, title="Service test", price_label="3 000 XAF")
        contact = BusinessWhatsAppContact.objects.create(business=self.business, phone="+" + self.sender, consent_service=True)

        def order():
            draft = WhatsAppDraftOrder.objects.create(
                business=self.business, contact=contact, connection=self.connection, catalog_item=item,
                unit_price=3000, total_price=3000, status=WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION,
            )
            return draft, confirm_draft_order(contact.phone, "oui", business=self.business)["transaction"]

        with override_settings(WHATSAPP_CAMPAY_BUSINESS_IDS=str(self.business.pk)):
            first, payment = order()
        self.assertEqual([case.pk for case in self.cases("paiements")], [first.pk])
        payment.ref_operateur = "follow-up-verification"
        payment.save(update_fields=["ref_operateur"])
        provider = Mock(mode="sandbox")
        provider.get_transaction.return_value = {
            "reference": payment.ref_operateur, "amount": "3000", "currency": "XAF", "status": "SUCCESSFUL",
        }
        reconcile_transaction(payment, provider)
        self.assertEqual([case.pk for case in self.cases("paiements")], [first.pk])
        provider.mode = "production"
        reconcile_transaction(payment, provider)
        self.assertEqual(self.cases("paiements"), [])

        second, manual_payment = order()
        close_url = reverse("whatsapp_commerce:follow_up_close", args=[self.business.pk, "paiements", second.pk])
        self.client.post(close_url)
        self.assertEqual(self.cases("paiements"), [])
        manual_payment.refresh_from_db()
        self.assertEqual(manual_payment.statut, "pending_awaiting_manual_validation")
