from datetime import time, timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile
from immobilier_cameroun.models import Bien, StatutBien, StatutVisite
from payments.campay import reconcile_transaction
from salonhub.bookings.models import Appointment
from salonhub.salons.models import OpeningHour, Salon, Service

from .inbox import _save_inbound
from .follow_ups import review_cases
from .models import BusinessWhatsAppActivation, BusinessWhatsAppBooking, BusinessWhatsAppConnection, WhatsAppDraftOrder, WhatsAppOfferClick
from .reply_jobs import process_reply_job


@override_settings(WHATSAPP_COMMERCE_AI_ENABLED=True, CAMPAY_PUBLIC_BASE_URL="https://e-shelle.com")
class OfferTrackingTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="offers-owner")
        self.business, self.connection, self.activation = self.profile("Restaurant Test", BusinessProfile.Module.RESTO, 1)
        self.item = BusinessCatalogItem.objects.create(
            business=self.business, title="Poulet braisé", item_type=BusinessCatalogItem.ItemType.MENU,
            price_label="4 500 F CFA", stock_quantity=5,
        )
        self.sender = "237699000055"
        self.sequence = 0

    def profile(self, name, module, number):
        business = BusinessProfile.objects.create(
            owner=self.owner, module=module, name=name, city="Douala", plan=BusinessProfile.Plan.BUSINESS,
            activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=10), ai_credits=25,
        )
        connection = BusinessWhatsAppConnection.objects.create(
            business=business, waba_id=f"waba-{number}", phone_number_id=f"phone-{number}",
            display_phone_number=f"+23769900009{number}",
            status=BusinessWhatsAppConnection.Status.ACTIVE, agent_enabled=True,
        )
        connection.set_access_token("mock-token")
        connection.save(update_fields=["access_token_encrypted"])
        activation = BusinessWhatsAppActivation.objects.create(connection=connection, assist_sales=True)
        return business, connection, activation

    def item_click(self, item):
        return reverse("whatsapp_commerce:catalogue_offer_whatsapp", args=[item.business.public_slug, item.pk])

    def prefilled_message(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).hostname, "wa.me")
        return parse_qs(urlsplit(response.url).query)["text"][0]

    def send(self, body, *, connection=None, sender=None, process=True):
        self.sequence += 1
        payload = {"id": f"offers-in-{self.sequence}", "from": sender or self.sender, "type": "text", "text": {"body": body}}
        _, message, _ = _save_inbound(connection or self.connection, payload, "", timezone.now())
        if not process:
            return message, payload
        with patch("whatsapp_commerce.inbox._request_meta", return_value={
            "messages": [{"id": f"offers-out-{self.sequence}"}],
        }) as meta:
            self.assertTrue(process_reply_job(message.reply_job.pk))
        return meta.call_args.kwargs["payload"]["text"]["body"] if meta.called else ""

    def report_row(self, business, offer, *, estate=False):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("whatsapp_commerce:offer_report", args=[business.pk]))
        self.assertContains(response, "Résultats par offre")
        return next(row for row in response.context["listings" if estate else "items"] if row.pk == offer.pk)

    def agenda(self, activation, service_name):
        salon = Salon.objects.create(owner=self.owner, name="Agenda", city="Douala", whatsapp_number=self.sender)
        service = Service.objects.create(salon=salon, name=service_name, price=0, duration_minutes=60)
        activation.booking_service = service
        activation.save(update_fields=["booking_service"])
        day = timezone.localdate() + timedelta(days=1)
        OpeningHour.objects.create(salon=salon, weekday=day.weekday(), start_time=time(9), end_time=time(15))
        return day

    def test_restaurant_report_counts_only_received_conversations_and_verified_payments(self):
        path = reverse("whatsapp_commerce:catalogue_offer", args=[self.business.public_slug, self.item.pk])
        self.assertContains(self.client.get(path), self.item.title)
        self.assertFalse(WhatsAppOfferClick.objects.exists())
        click = self.item_click(self.item)
        self.client.get(click, headers={"Sec-Purpose": "prefetch"})
        self.assertFalse(WhatsAppOfferClick.objects.exists())
        message = self.prefilled_message(click)
        row = self.report_row(self.business, self.item)
        self.assertEqual((row.click_count, row.conversation_count, row.paid_count), (1, 0, 0))
        self.assertIn(path, row.share_url)
        self.assertIn(self.item.title, self.send(message))
        self.send(self.prefilled_message(click))
        row = self.report_row(self.business, self.item)
        self.assertEqual((row.click_count, row.conversation_count, row.paid_count), (2, 1, 0))
        with override_settings(WHATSAPP_CAMPAY_BUSINESS_IDS=str(self.business.pk)):
            self.assertIn("9 000", self.send("COMMANDER 2 x"))
            self.assertIn("confirmée", self.send("OUI"))
        draft = WhatsAppDraftOrder.objects.get(catalog_item=self.item)
        self.assertEqual(draft.source_click.catalog_item, self.item)
        payment = draft.payment_transaction
        self.assertEqual(self.report_row(self.business, self.item).paid_count, 0)
        payment.ref_operateur = "test-ref"
        payment.save(update_fields=["ref_operateur"])
        provider = Mock(mode="sandbox")
        provider.get_transaction.return_value = {"reference": "test-ref", "currency": "XAF", "amount": "9000", "status": "SUCCESSFUL"}
        reconcile_transaction(payment, provider)
        self.assertEqual(self.report_row(self.business, self.item).paid_count, 0)
        provider.mode = "production"
        reconcile_transaction(payment, provider)
        self.assertEqual(self.report_row(self.business, self.item).paid_count, 1)
        payment.refresh_from_db()
        payment.statut = "rembourse"
        payment.save(update_fields=["statut"])
        self.assertEqual(self.report_row(self.business, self.item).paid_count, 0)

    def test_agency_visit_is_attributed_to_the_correct_listing_and_report_keeps_one_result(self):
        agency, connection, activation = self.profile("Agence Test", BusinessProfile.Module.IMMOBILIER, 2)
        listing = Bien.objects.create(
            agence=agency, proprietaire=self.owner, titre="Appartement Bonapriso", ville="Douala",
            quartier="Bonapriso", prix=250000, statut=StatutBien.PUBLIE,
        )
        day = self.agenda(activation, "Visite")
        click = reverse("immobilier:whatsapp_bien", args=[listing.slug])
        message = self.prefilled_message(click)
        self.assertIn(f"BIEN {listing.pk}", message)
        self.assertIn(listing.titre, self.send(message, connection=connection))
        self.assertEqual(self.report_row(agency, listing, estate=True).booking_count, 0)
        self.assertIn("Visite confirmée", self.send(f"RDV {day} 09:00", connection=connection))
        booking = BusinessWhatsAppBooking.objects.get()
        self.assertEqual(booking.source_click.property_listing, listing)
        self.assertIn("Visite reportée", self.send(f"REPORTER {booking.appointment_id} {day} 11:00", connection=connection))
        row = self.report_row(agency, listing, estate=True)
        self.assertEqual((row.click_count, row.conversation_count, row.booking_count), (1, 1, 1))
        booking.property_visit.statut = StatutVisite.ANNULE
        booking.property_visit.save(update_fields=["statut"])
        self.assertEqual(self.report_row(agency, listing, estate=True).booking_count, 0)

    def test_services_match_the_active_agenda_and_reference_is_isolated(self):
        salon, connection, activation = self.profile("Salon Test", BusinessProfile.Module.SERVICES, 3)
        item = BusinessCatalogItem.objects.create(business=salon, title="Diagnostic", item_type="service", price_label="3 000 XAF")
        day = self.agenda(activation, "Diagnostic")
        message = self.prefilled_message(self.item_click(item))
        self.send(message, process=False)
        self.assertIsNone(WhatsAppOfferClick.objects.get().entry_message_id)
        self.assertIn("Écris RDV", self.send(message, connection=connection))
        self.send(message, connection=connection, sender="237699000057", process=False)
        self.assertIn("Rendez-vous confirmé", self.send(f"RDV {day} 09:00", connection=connection))
        row = self.report_row(salon, item)
        self.assertEqual((row.click_count, row.conversation_count, row.booking_count), (1, 1, 1))
        Appointment.objects.update(status=Appointment.Status.CANCELLED)
        self.assertEqual(self.report_row(salon, item).booking_count, 0)
        self.client.force_login(get_user_model().objects.create_user(username="offers-outsider"))
        self.assertEqual(self.client.get(reverse("whatsapp_commerce:offer_report", args=[salon.pk])).status_code, 404)
        other_path = reverse("whatsapp_commerce:catalogue_offer", args=[self.business.public_slug, item.pk])
        self.assertEqual(self.client.get(other_path).status_code, 404)

    def test_no_payment_from_a_stale_price_or_an_unsupported_currency(self):
        self.send(self.prefilled_message(self.item_click(self.item)))
        self.assertIn("4 500", self.send("COMMANDER"))
        BusinessCatalogItem.objects.filter(pk=self.item.pk).update(price_label="5 000 XAF")
        self.assertIn("nouveau récapitulatif", self.send("OUI"))
        self.assertEqual(WhatsAppDraftOrder.objects.get().status, WhatsAppDraftOrder.Status.CANCELLED)
        BusinessCatalogItem.objects.filter(pk=self.item.pk).update(price_label="15 EUR")
        self.assertIn("prix de cet article", self.send("COMMANDER"))
        self.assertFalse(WhatsAppDraftOrder.objects.filter(status=WhatsAppDraftOrder.Status.CONFIRMED).exists())
        self.assertEqual(review_cases(self.business).get().follow_up_item, self.item)
