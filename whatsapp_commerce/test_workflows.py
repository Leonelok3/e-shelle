from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile
from salonhub.bookings.models import Appointment
from salonhub.salons.models import OpeningHour, Salon, Service

from .automations import send_scheduled_template_message
from .follow_ups import booking_cases, review_cases
from .inbox import _save_inbound
from .models import BusinessWhatsAppBooking, BusinessWhatsAppConnection, BusinessWhatsAppContact, BusinessWhatsAppWorkflow, ScheduledBusinessWhatsAppMessage, WhatsAppDraftOrder
from .orchestrator import confirm_draft_order
from .reply_jobs import process_reply_job
from .workflows import BUTTONS, Kind, Status, plan_workflows


@override_settings(WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True, CAMPAY_PUBLIC_BASE_URL="https://e-shelle.com")
class WorkflowTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="workflow-owner")
        self.business = BusinessProfile.objects.create(
            owner=self.owner, name="Agenda et commerce", city="Douala", module=BusinessProfile.Module.SERVICES,
            plan=BusinessProfile.Plan.BUSINESS, activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=10),
        )
        self.connection = BusinessWhatsAppConnection.objects.create(
            business=self.business, waba_id="workflow-waba", phone_number_id="workflow-number",
            status=BusinessWhatsAppConnection.Status.ACTIVE, automations_enabled=True,
        )
        self.connection.set_access_token("workflow-test-token")
        self.connection.save(update_fields=["access_token_encrypted"])
        self.contact = BusinessWhatsAppContact.objects.create(
            business=self.business, phone="+237699000012", consent_service=True, consent_marketing=True,
        )
        self.seq = 0

    def rule(self, kind, hours=1):
        rule = BusinessWhatsAppWorkflow.objects.create(
            business=self.business, kind=kind, enabled=True, delay_hours=hours, template_name=f"test_{kind}",
        )
        BusinessWhatsAppWorkflow.objects.filter(pk=rule.pk).update(updated_at=timezone.now() - timedelta(days=3))
        return rule

    def booking(self, day, slot=time(9)):
        salon = Salon.objects.create(owner=self.owner, name="Agenda", city="Douala", whatsapp_number=self.contact.phone)
        service = Service.objects.create(salon=salon, name="Diagnostic", price=0, duration_minutes=60)
        appointment = Appointment.objects.create(
            salon=salon, service=service, date=day, time=slot, client_name="Client", client_phone=self.contact.phone,
            status=Appointment.Status.CONFIRMED,
        )
        return BusinessWhatsAppBooking.objects.create(appointment=appointment, contact=self.contact)

    def draft_order(self):
        item = BusinessCatalogItem.objects.create(business=self.business, title="Produit", price_label="2000 XAF")
        draft = WhatsAppDraftOrder.objects.create(
            business=self.business, connection=self.connection, contact=self.contact, catalog_item=item,
            status=WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION, unit_price=2000, total_price=2000,
        )
        with override_settings(WHATSAPP_CAMPAY_BUSINESS_IDS=str(self.business.pk)):
            confirm_draft_order(self.contact.phone, "oui", business=self.business)
        draft.refresh_from_db()
        return draft

    def deliver(self, scheduled):
        template = {"category": "UTILITY", "components": [{"type": "BODY", "text": "Ton opération {{1}} chez {{2}}."}, {
            "type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": label} for _, label in BUTTONS[scheduled.workflow.kind]],
        }]}
        with patch("whatsapp_commerce.automations._find_approved_template", return_value=template), patch(
            "whatsapp_commerce.automations._request_meta", return_value={"messages": [{"id": f"workflow-sent-{scheduled.pk}"}]},
        ) as meta:
            sent = send_scheduled_template_message(scheduled.pk)
        scheduled.refresh_from_db()
        return sent, meta.call_args.kwargs["payload"]["template"] if meta.called else None

    def inbound(self, *, text=None, payload=None, context=None, phone=None):
        self.seq += 1
        inbound = {"id": f"workflow-in-{self.seq}", "from": phone or self.contact.phone}
        if payload:
            inbound.update(type="button", button={"text": "Action", "payload": payload})
        else:
            inbound.update(type="text", text={"body": text})
        if context:
            inbound["context"] = {"id": context}
        _, message, _ = _save_inbound(self.connection, inbound, "Client", timezone.now())
        with patch("whatsapp_commerce.inbox._request_meta", return_value={"messages": [{"id": f"workflow-out-{self.seq}"}]}):
            self.assertTrue(process_reply_job(message.reply_job.pk))
        message.reply_job.refresh_from_db()
        return message.reply_job

    def test_reminder_has_two_buttons_is_scoped_to_contact_and_reschedules_only_once(self):
        self.rule(Kind.BOOKING, 48)
        day = timezone.localdate() + timedelta(days=1)
        booking = self.booking(day)
        OpeningHour.objects.create(salon=booking.appointment.salon, weekday=day.weekday(), start_time=time(8), end_time=time(17))
        plan_workflows()
        plan_workflows()
        scheduled = ScheduledBusinessWhatsAppMessage.objects.get()
        sent, template = self.deliver(scheduled)
        self.assertTrue(sent)
        confirms, reports = [part["parameters"][0]["payload"] for part in template["components"] if part["type"] == "button"]
        self.inbound(payload=confirms, context=scheduled.wa_message_id, phone="+237699000013")
        booking.refresh_from_db()
        self.assertIsNone(booking.presence_confirmed_at)
        self.inbound(payload=confirms, context=scheduled.wa_message_id)
        booking.refresh_from_db()
        self.assertIsNotNone(booking.presence_confirmed_at)
        self.inbound(payload=reports, context=scheduled.wa_message_id)
        self.inbound(text=f"REPORTER {booking.appointment_id} {day} 11:00")
        booking.refresh_from_db()
        scheduled.refresh_from_db()
        self.assertEqual(booking.appointment.time, time(11))
        self.assertIsNone(booking.presence_confirmed_at)
        self.assertEqual(scheduled.workflow_action, "rescheduled")
        self.inbound(payload=confirms, context=scheduled.wa_message_id)
        booking.refresh_from_db()
        self.assertIsNone(booking.presence_confirmed_at)
        plan_workflows()
        self.assertEqual(ScheduledBusinessWhatsAppMessage.objects.count(), 2)

    def test_pending_campay_reminder_rechecks_payment_after_planning(self):
        self.rule(Kind.PAYMENT)
        draft = self.draft_order()
        WhatsAppDraftOrder.objects.filter(pk=draft.pk).update(confirmed_at=timezone.now() - timedelta(hours=2))
        with override_settings(WHATSAPP_CAMPAY_BUSINESS_IDS=str(self.business.pk)):
            plan_workflows()
            scheduled = ScheduledBusinessWhatsAppMessage.objects.get(workflow_order=draft)
            payment = draft.payment_transaction
            payment.statut = "pending_awaiting_manual_validation"
            payment.metadata = {"campay": {"mode": "production", "provider_status": "SUCCESSFUL", "verified_at": timezone.now().isoformat()}}
            payment.save(update_fields=["statut", "metadata"])
            self.assertEqual(self.deliver(scheduled), (False, None))
        self.assertEqual(scheduled.status, Status.CANCELLED)

    def test_valid_payment_reminder_reuses_checkout_without_storing_its_link(self):
        self.rule(Kind.PAYMENT)
        draft = self.draft_order()
        WhatsAppDraftOrder.objects.filter(pk=draft.pk).update(confirmed_at=timezone.now() - timedelta(hours=2))
        with override_settings(WHATSAPP_CAMPAY_BUSINESS_IDS=str(self.business.pk)):
            plan_workflows()
            scheduled = ScheduledBusinessWhatsAppMessage.objects.get(workflow_order=draft)
            sent, template = self.deliver(scheduled)
        self.assertTrue(sent)
        body, = template["components"]
        self.assertEqual(body["parameters"][0]["text"], draft.boutique_order.reference)
        self.assertTrue(body["parameters"][1]["text"].startswith("https://e-shelle.com/"))
        self.assertEqual(scheduled.body_parameters, [])

    def test_completion_follow_ups_and_feedback_reach_the_team(self):
        booking_rule = self.rule(Kind.AFTER_BOOKING)
        self.rule(Kind.AFTER_ORDER)
        booking = self.booking(timezone.localdate() - timedelta(days=1))
        draft = self.draft_order()
        order = draft.boutique_order
        order.statut = "payee"
        order.save(update_fields=["statut", "updated_at"])
        self.client.force_login(self.owner)
        url = reverse("whatsapp_commerce:business_workflows", args=[self.business.pk])
        self.assertContains(self.client.get(url), "Historique des automatisations")
        for subject, pk in [("booking", booking.pk), ("order", draft.pk)]:
            self.client.post(reverse("whatsapp_commerce:workflow_complete", args=[self.business.pk, subject, pk]))
        booking.refresh_from_db()
        order.refresh_from_db()
        self.assertIsNotNone(booking.completed_at)
        self.assertEqual(order.statut, "livree")
        BusinessWhatsAppBooking.objects.filter(pk=booking.pk).update(completed_at=timezone.now() - timedelta(hours=2))
        type(order).objects.filter(pk=order.pk).update(updated_at=timezone.now() - timedelta(hours=2))
        plan_workflows()
        self.assertEqual(ScheduledBusinessWhatsAppMessage.objects.count(), 2)
        appointment_message = ScheduledBusinessWhatsAppMessage.objects.get(workflow=booking_rule)
        self.assertTrue(self.deliver(appointment_message)[0])
        self.inbound(text="Je souhaite poursuivre", context=appointment_message.wa_message_id)
        self.assertEqual(review_cases(self.business).get().message.body, "Je souhaite poursuivre")

    def test_no_slots_opens_a_handoff_and_paused_rules_do_not_send(self):
        rule = self.rule(Kind.BOOKING, 48)
        booking = self.booking(timezone.localdate() + timedelta(days=1))
        plan_workflows()
        message = ScheduledBusinessWhatsAppMessage.objects.get()
        self.assertTrue(self.deliver(message)[0])
        self.inbound(payload=f"esflow:{message.workflow_token.hex}:reschedule", context=message.wa_message_id)
        self.assertEqual(booking_cases(self.business).get().follow_up_appointment_id, booking.appointment_id)
        appointment = booking.appointment
        appointment.time = time(10)
        appointment.save(update_fields=["time"])
        plan_workflows()
        pending = ScheduledBusinessWhatsAppMessage.objects.get(status=Status.SCHEDULED)
        rule.enabled = False
        rule.save(update_fields=["enabled"])
        self.assertEqual(self.deliver(pending), (False, None))
        self.assertEqual(pending.status, Status.CANCELLED)
        rule.enabled = True
        rule.save(update_fields=["enabled", "updated_at"])
        plan_workflows()
        pending.refresh_from_db()
        self.assertEqual(pending.status, Status.SCHEDULED)
        self.assertTrue(self.deliver(pending)[0])
