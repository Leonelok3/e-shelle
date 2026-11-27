from datetime import time, timedelta
from decimal import Decimal
from hashlib import sha256
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessLeadEvent, BusinessProfile
from payments.campay import reconcile_transaction
from salonhub.bookings.models import Appointment
from salonhub.bookings.utils import get_available_slots
from salonhub.salons.models import OpeningHour, Salon, Service

from .bookings import booking_reply
from .checkout import checkout_url, payment_status
from .inbox import _save_inbound
from .models import BusinessWhatsAppActivation, BusinessWhatsAppConnection, BusinessWhatsAppContact, WhatsAppDraftOrder
from .orchestrator import confirm_draft_order
from .reply_jobs import process_reply_job


@override_settings(WHATSAPP_COMMERCE_AI_ENABLED=True)
class BusinessAgentsTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="agent-owner")
        self.business = BusinessProfile.objects.create(
            owner=self.owner, module=BusinessProfile.Module.SERVICES, name="Atelier E-Shelle", city="Douala",
            plan=BusinessProfile.Plan.BUSINESS, activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=10), ai_credits=5,
        )
        self.connection = BusinessWhatsAppConnection.objects.create(
            business=self.business, waba_id="agents-waba", phone_number_id="agents-phone",
            status=BusinessWhatsAppConnection.Status.ACTIVE, agent_enabled=True,
        )
        self.contact = BusinessWhatsAppContact.objects.create(
            business=self.business, phone="+237699000054", consent_service=True,
        )
        self.activation = BusinessWhatsAppActivation.objects.create(
            connection=self.connection, opening_hours="Lundi 09 h–18 h",
        )

    @override_settings(CAMPAY_PUBLIC_BASE_URL="https://e-shelle.com")
    @patch("payments.views.CampayClient")
    def test_signed_checkout_is_reused_and_verified_by_provider(self, provider):
        provider.return_value.mode = "sandbox"
        provider.return_value.create_payment_link.return_value = (
            "https://www.campay.net/pay/mock", "approved-reference",
        )
        item = BusinessCatalogItem.objects.create(business=self.business, title="Diagnostic")
        draft = WhatsAppDraftOrder.objects.create(
            business=self.business, connection=self.connection, contact=self.contact, catalog_item=item,
            unit_price=Decimal("4000"), total_price=Decimal("4000"),
            status=WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION,
        )
        with override_settings(WHATSAPP_CAMPAY_BUSINESS_IDS=str(self.business.pk)):
            confirmation = confirm_draft_order(self.contact.phone, "oui", business=self.business)
            payment = confirmation["transaction"]
            self.assertEqual((payment.methode, payment_status(payment)), ("campay", "Paiement en attente"))
            path = urlsplit(checkout_url(payment)).path
            self.assertContains(self.client.get(path), "Continuer vers le paiement")
            provider.return_value.create_payment_link.assert_not_called()
            self.assertEqual(self.client.post(path).url, "https://www.campay.net/pay/mock")
            self.assertEqual(self.client.post(path).url, "https://www.campay.net/pay/mock")
            provider.return_value.create_payment_link.assert_called_once()
            self.assertEqual(self.client.get(path.rstrip("/") + "a/").status_code, 404)
            payment.refresh_from_db()
            reconciliation = Mock(mode="sandbox")
            result = {"reference": payment.ref_operateur, "currency": "XAF", "amount": "4000"}
            reconciliation.get_transaction.side_effect = [
                {**result, "status": "SUCCESSFUL"}, {**result, "status": "PENDING"},
            ]
            reconcile_transaction(payment, reconciliation)
            reconcile_transaction(payment, reconciliation)
            self.assertContains(self.client.get(path), "Paiement de test vérifié")
            self.client.force_login(self.owner)
            dashboard = reverse("whatsapp_commerce:business_dashboard", args=[self.business.pk])
            self.assertContains(self.client.get(dashboard), "Paiement de test vérifié")
        draft.refresh_from_db()
        self.assertEqual(draft.boutique_order.statut, "en_attente")

    @patch("whatsapp_commerce.inbox._request_meta", return_value={"messages": [{"id": "agents-out-booking"}]})
    def test_shared_agenda_blocks_overlaps_and_reschedules_only_own_appointment(self, meta):
        salon = Salon.objects.create(owner=self.owner, name="Atelier", city="Douala", whatsapp_number="237699000053")
        service = Service.objects.create(salon=salon, name="Diagnostic", price=3000, duration_minutes=60)
        day = timezone.localdate() + timedelta(days=1)
        OpeningHour.objects.create(salon=salon, weekday=day.weekday(), start_time=time(9), end_time=time(18))
        self.activation.booking_service = service
        self.activation.save(update_fields=["booking_service"])
        self.assertIn(f"RDV {day} 09:00", booking_reply(self.activation, self.contact, "rendez-vous"))
        self.connection.set_access_token("mock-token")
        self.connection.save(update_fields=["access_token_encrypted"])
        _, inbound, _ = _save_inbound(self.connection, {
            "from": self.contact.phone, "id": "agent-booking", "type": "text",
            "text": {"body": f"RDV {day} 09:00"},
        }, "", timezone.now())
        self.assertTrue(process_reply_job(inbound.reply_job.pk))
        self.assertIn("Rendez-vous confirmé", meta.call_args.kwargs["payload"]["text"]["body"])
        self.assertNotIn(time(9, 30), get_available_slots(salon, day, service))
        appointment = Appointment.objects.get(salon=salon)
        other = BusinessWhatsAppContact.objects.create(business=self.business, phone="+237699000055")
        command = f"REPORTER {appointment.pk} {day} 11:00"
        self.assertIn("introuvable", booking_reply(self.activation, other, command))
        self.assertIn("Rendez-vous reporté", booking_reply(self.activation, self.contact, command))
        appointment.refresh_from_db()
        self.assertEqual(appointment.time, time(11))
        self.assertFalse(Appointment.objects.filter(salon=salon, time=time(9)).exists())
        self.client.force_login(self.owner)
        response = self.client.get(reverse("whatsapp_commerce:business_dashboard", args=[self.business.pk]))
        self.assertEqual(response.context["agent_metrics"]["appointments_upcoming"], 1)

    @override_settings(WHATSAPP_INBOUND_VOICE_ENABLED=True, OPENAI_API_KEY="mock-key")
    @patch("whatsapp_commerce.inbox._request_meta", return_value={"messages": [{"id": "agents-out-voice"}]})
    @patch("whatsapp_commerce.voice.transcribe_voice", return_value="Quels sont vos horaires ?")
    def test_voice_is_transcribed_by_worker_and_can_answer_hours(self, transcribe, meta):
        self.connection.set_access_token("mock-token")
        self.connection.save(update_fields=["access_token_encrypted"])
        self.activation.voice_enabled = True
        self.activation.save(update_fields=["voice_enabled"])
        _, message, _ = _save_inbound(
            self.connection, {"id": "agents-voice", "from": "237699000054", "type": "audio", "audio": {"id": "123456"}},
            "", timezone.now(),
        )
        transcribe.assert_not_called()
        self.assertTrue(process_reply_job(message.reply_job.pk))
        transcribe.assert_called_once()
        self.assertEqual(transcribe.call_args.args[1].media_id, "123456")
        self.assertIn("Lundi", meta.call_args.kwargs["payload"]["text"]["body"])
        message.refresh_from_db()
        self.assertEqual(message.body, "Quels sont vos horaires ?")
        self.business.refresh_from_db()
        self.assertEqual(self.business.ai_credits, 4)

    def test_visibility_previews_clicks_and_protects_owner_saved_description(self):
        BusinessLeadEvent.objects.create(business=self.business, event_type="whatsapp", source="profile")
        BusinessLeadEvent.objects.create(business=self.business, event_type="whatsapp", source="home")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("business:dashboard"), {"business": self.business.pk})
        self.assertEqual(response.context["visibility"]["profile_clicks"], 1)
        url = reverse("business:business_visibility_apply", args=[self.business.pk])
        version = sha256(b"").hexdigest()
        self.client.post(url, {"description": "Description relue et publiée.", "version": version})
        self.client.post(url, {"description": "Onglet ancien.", "version": version})
        self.business.refresh_from_db()
        self.assertEqual(self.business.description, "Description relue et publiée.")
        other = get_user_model().objects.create_user(username="agent-other-owner")
        self.client.force_login(other)
        self.assertEqual(self.client.post(url, {"description": "Intrus", "version": version}).status_code, 404)

    def test_home_uses_new_brand_promise(self):
        response = self.client.get("/")
        self.assertContains(response, "E‑Shelle, la plateforme qui transforme votre conversation WhatsApp")
        self.assertContains(response, "commande payée ou en rendez-vous confirmé")
