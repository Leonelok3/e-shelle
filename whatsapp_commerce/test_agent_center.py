from datetime import time, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile
from immobilier_cameroun.models import Bien, StatutBien
from salonhub.salons.models import OpeningHour, Salon, Service
from whatsapp_agent.models import Campagne

from .automations import send_scheduled_template_message
from .models import BusinessWhatsAppActivation, BusinessWhatsAppConnection, BusinessWhatsAppContact, BusinessWhatsAppReplyJob, BusinessWhatsAppWorkflow, ScheduledBusinessWhatsAppMessage, WhatsAppCatalogChange, WhatsAppDraftOrder, WhatsAppOfferClick, WhatsAppQuote, WhatsAppStockHold, WhatsAppWatch
from .orchestrator import confirm_draft_order
from .order_operations import customer_order_reply, receipt_token
from .quote_views import accept_quote
from .watches import customer_watch_reply
from .workflows import plan_workflows


@override_settings(WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True)
class AgentCenterTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="agent-center-owner", email="owner@example.test")
        self.business = self.profile("Commerce", BusinessProfile.Module.SERVICES)
        self.connection = BusinessWhatsAppConnection.objects.create(
            business=self.business, waba_id="center-waba", phone_number_id="center-phone",
            status=BusinessWhatsAppConnection.Status.ACTIVE, automations_enabled=True,
        )
        self.connection.set_access_token("center-test-token")
        self.connection.save(update_fields=["access_token_encrypted"])
        self.contact = self.customer("+237699123456")
        self.client.force_login(self.owner)

    def profile(self, name, module):
        return BusinessProfile.objects.create(
            name=name, module=module, owner=self.owner, city="Douala", plan=BusinessProfile.Plan.BUSINESS,
            activation_status=BusinessProfile.ActivationStatus.ACTIVE, subscription_expires_at=timezone.now() + timedelta(days=7),
        )

    def customer(self, number):
        return BusinessWhatsAppContact.objects.create(business=self.business, phone=number, consent_service=True, consent_marketing=True)

    def draft(self, contact, item, qty):
        return WhatsAppDraftOrder.objects.create(
            contact=contact, business=self.business, connection=self.connection, catalog_item=item,
            quantity=qty, unit_price=1500, total_price=1500 * qty, status=WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION,
        )

    def test_private_center_and_digest_for_owner(self):
        url = reverse("whatsapp_commerce:agent_center", args=[self.business.pk])
        self.assertContains(self.client.get(url), "Continuer la mise en route")
        self.assertContains(self.client.get(url), "Gérer les devis")
        self.client.post(reverse("whatsapp_commerce:agent_digest", args=[self.business.pk]))
        self.assertEqual(mail.outbox[0].to, [self.owner.email])
        self.client.force_login(get_user_model().objects.create_user(username="outside-center"))
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_stock_reservation_cancellation_and_paid_receipt(self):
        item = BusinessCatalogItem.objects.create(business=self.business, title="Lampe", stock_quantity=2)
        first = self.draft(self.contact, item, 2)
        other = self.customer("+237699123458")
        second = self.draft(other, item, 1)
        result = confirm_draft_order(self.contact.phone, "oui", business=self.business)
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(confirm_draft_order(self.contact.phone, "oui", business=self.business)["status"], "already_confirmed")
        self.assertEqual(confirm_draft_order(other.phone, "oui", business=self.business)["status"], "catalog_offer_changed")
        item.refresh_from_db()
        self.assertEqual(item.stock_quantity, 0)
        update = reverse("whatsapp_commerce:order_operations_update", args=[self.business.pk, first.pk])
        self.client.post(update, {"action": "cancel"})
        self.client.post(update, {"action": "cancel"})
        item.refresh_from_db()
        self.assertEqual(item.stock_quantity, 2)
        self.assertEqual(WhatsAppStockHold.objects.get(draft=first).status, WhatsAppStockHold.Status.RELEASED)
        second = self.draft(other, item, 1)
        result = confirm_draft_order(other.phone, "oui", business=self.business)
        order, payment = result["order"], result["transaction"]
        token = receipt_token(result["draft"])
        receipt = reverse("whatsapp_commerce:order_receipt", args=[token])
        self.assertEqual(self.client.get(receipt).status_code, 404)
        payment.statut = "succes"
        payment.save(update_fields=["statut"])
        BusinessWhatsAppWorkflow.objects.create(business=self.business, kind="shipping", enabled=True, delay_hours=0, template_name="shipped")
        update = reverse("whatsapp_commerce:order_operations_update", args=[self.business.pk, second.pk])
        self.client.post(update, {"action": "shipped", "delivery_note": "Livraison cet après-midi"})
        plan_workflows()
        shipping = ScheduledBusinessWhatsAppMessage.objects.get(workflow_order=second)
        self.assertContains(self.client.get(receipt), order.reference)
        job = BusinessWhatsAppReplyJob()
        self.assertIn("Expédiée", customer_order_reply(other, f"SUIVI {order.reference}", job)[0])
        self.assertIn("introuvable", customer_order_reply(self.contact, f"SUIVI {order.reference}", job)[0])
        self.assertTrue(customer_order_reply(other, f"SAV {order.reference} Il manque un article", job)[1])
        self.assertEqual(job.follow_up_order_id, second.pk)
        self.client.post(update, {"action": "delivered"})
        self.assertEqual(WhatsAppStockHold.objects.get(draft=second).status, WhatsAppStockHold.Status.CONSUMED)
        template = {"category": "UTILITY", "components": [{"type": "BODY", "text": "La commande {{1}} est expédiée. {{2}}"}]}
        with patch("whatsapp_commerce.automations._find_approved_template", return_value=template), patch("whatsapp_commerce.automations._request_meta") as send:
            self.assertFalse(send_scheduled_template_message(shipping.pk))
            send.assert_not_called()

    def test_quote_is_validated_once_and_can_only_be_accepted_by_its_contact(self):
        quotes = reverse("whatsapp_commerce:quotes", args=[self.business.pk])
        self.assertEqual(self.client.post(quotes, {
            "contact": self.contact.pk, "subject": "Installation", "description": "Pose et essai",
            "amount": "25000", "currency": "XAF", "valid_until": timezone.localdate().isoformat(),
        }).status_code, 302)
        quote = WhatsAppQuote.objects.get()
        update = reverse("whatsapp_commerce:quote_update", args=[self.business.pk, quote.pk])
        with patch("whatsapp_commerce.quote_views.send_business_reply") as send:
            self.client.post(update, {"action": "send"})
            self.client.post(update, {"action": "send"})
            send.assert_called_once()
        other = self.customer("+237699123457")
        self.assertFalse(accept_quote(other, f"ACCEPTER DEVIS {quote.code}")[1])
        self.assertTrue(accept_quote(self.contact, f"ACCEPTER DEVIS {quote.code}")[1])
        self.assertFalse(accept_quote(self.contact, f"ACCEPTER DEVIS {quote.code}")[1])

    def test_waitlist_notifies_once_and_can_be_cancelled(self):
        salon = Salon.objects.create(owner=self.owner, name="Agenda attente", city="Douala", whatsapp_number=self.contact.phone)
        service = Service.objects.create(salon=salon, name="Diagnostic", price=0, duration_minutes=60)
        BusinessWhatsAppActivation.objects.create(connection=self.connection, booking_service=service)
        BusinessWhatsAppWorkflow.objects.create(business=self.business, kind="waitlist", enabled=True, delay_hours=1, template_name="waitlist")
        self.assertIn("prochain créneau", customer_watch_reply(self.connection, self.contact, "LISTE D’ATTENTE")[0])
        WhatsAppWatch.objects.update(requested_at=timezone.now() - timedelta(hours=2))
        plan_workflows()
        self.assertFalse(ScheduledBusinessWhatsAppMessage.objects.exists())
        day = timezone.localdate() + timedelta(days=1)
        OpeningHour.objects.create(salon=salon, weekday=day.weekday(), start_time=time(9), end_time=time(11))
        plan_workflows()
        plan_workflows()
        row = ScheduledBusinessWhatsAppMessage.objects.get()
        customer_watch_reply(self.connection, self.contact, "STOP ALERTES")
        template = {"category": "UTILITY", "components": [{"type": "BODY", "text": "Une place pour {{1}} est disponible {{2}}."}]}
        with patch("whatsapp_commerce.automations._find_approved_template", return_value=template), patch("whatsapp_commerce.automations._request_meta") as send:
            self.assertFalse(send_scheduled_template_message(row.pk))
            send.assert_not_called()

    def test_property_match_respects_the_agency_and_saved_search(self):
        from .watches import match_watch

        agency = self.profile("Agence", BusinessProfile.Module.IMMOBILIER)
        second = self.profile("Autre agence", BusinessProfile.Module.IMMOBILIER)
        contact = BusinessWhatsAppContact.objects.create(business=agency, phone=self.contact.phone)
        watch = WhatsAppWatch.objects.create(contact=contact, kind="property_alert", requested_at=timezone.now() - timedelta(days=1), criteria={"quartier__iexact": "Bonapriso"})
        for business, title, area in [(second, "Bien de l’autre agence", "Bonapriso"), (agency, "Autre quartier", "Akwa"), (agency, "Bien attendu", "Bonapriso")]:
            Bien.objects.create(agence=business, proprietaire=self.owner, titre=title, ville="Douala", quartier=area, prix=50000, statut=StatutBien.PUBLIE, date_publication=timezone.now())
        self.assertEqual(match_watch(watch)[1][0], "Bien attendu")

    @override_settings(WHATSAPP_COMMERCE_AI_ENABLED=True)
    def test_campaign_links_are_scoped_to_the_selected_offer_and_catalog_edits_are_audited(self):
        self.connection.agent_enabled = True
        self.connection.display_phone_number = self.contact.phone
        self.connection.save(update_fields=["agent_enabled", "display_phone_number"])
        BusinessWhatsAppActivation.objects.create(connection=self.connection)
        first = BusinessCatalogItem.objects.create(business=self.business, title="Article pilote", price_label="2000 FCFA")
        second = BusinessCatalogItem.objects.create(business=self.business, title="Autre article")
        first.price_label = "2600 FCFA"
        first.save(update_fields=["price_label"])
        history = WhatsAppCatalogChange.objects.filter(item=first).latest("created_at")
        self.assertEqual(history.changes, {"Prix": ["2000 FCFA", "2600 FCFA"]})
        campaign = Campagne.objects.create(business=self.business, nom="Pilote", message_template="Découvrez notre offre")
        response = self.client.get(reverse("whatsapp_commerce:business_campaign_detail", args=[self.business.pk, campaign.pk]), {"offre": f"article-{first.pk}"})
        self.assertContains(response, "Texte proposé à valider")
        link = response.context["campaign_offer_link"]
        token = parse_qs(urlsplit(link).query)["campagne"][0]
        for item in (first, second):
            contact_path = reverse("whatsapp_commerce:catalogue_offer_whatsapp", args=[self.business.public_slug, item.pk])
            self.assertEqual(self.client.get(contact_path, {"campagne": token}).status_code, 302)
        self.assertEqual(WhatsAppOfferClick.objects.get(catalog_item=first).campaign, campaign)
        self.assertIsNone(WhatsAppOfferClick.objects.get(catalog_item=second).campaign)
