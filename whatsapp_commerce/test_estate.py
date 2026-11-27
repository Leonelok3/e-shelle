from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessLeadEvent, BusinessProfile
from business.services import collect_business_items
from immobilier_cameroun.forms import BienForm
from immobilier_cameroun.models import Bien, DemandeVisite, PeriodePrix, StatutBien, StatutVisite
from salonhub.salons.models import OpeningHour, Salon, Service

from .activation import configuration_blockers, test_question as activation_question
from .inbox import _save_inbound
from .models import BusinessWhatsAppActivation, BusinessWhatsAppBooking, BusinessWhatsAppConnection
from .reply_jobs import process_reply_job


@override_settings(WHATSAPP_COMMERCE_AI_ENABLED=True)
class EstateAssistantTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="agency-owner")
        self.other_user = get_user_model().objects.create_user(username="agency-other-owner")
        self.agency = self.create_agency(self.owner, "Agence Horizon")
        self.another = self.create_agency(self.owner, "Agence secondaire")
        self.other_agency = self.create_agency(self.other_user, "Agence concurrente")
        self.target = self.create_listing(self.agency, "Appartement Horizon")
        self.create_listing(self.another, "Appartement autre agence du même compte")
        self.create_listing(self.other_agency, "Appartement tiers")
        self.create_listing(self.agency, "Appartement vendu", statut=StatutBien.LOUE_VENDU)
        self.create_listing(self.agency, "Appartement futur", date_disponibilite=timezone.localdate() + timedelta(days=60))
        self.create_listing(self.agency, "Appartement tarif journalier", periode_prix=PeriodePrix.PAR_JOUR)
        self.connection = BusinessWhatsAppConnection.objects.create(
            business=self.agency, waba_id="agency-waba", phone_number_id="agency-number",
            display_phone_number="+237699000063", status=BusinessWhatsAppConnection.Status.ACTIVE, agent_enabled=True,
        )
        self.connection.set_access_token("fake-token")
        self.connection.save(update_fields=["access_token_encrypted"])
        self.activation = BusinessWhatsAppActivation.objects.create(
            connection=self.connection, answer_hours=False, answer_catalog=False,
        )
        self.sequence = 0

    def create_agency(self, owner, name):
        return BusinessProfile.objects.create(
            owner=owner, module=BusinessProfile.Module.IMMOBILIER, name=name, city="Douala",
            plan=BusinessProfile.Plan.BUSINESS, activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=2), ai_credits=5,
        )

    def create_listing(self, agency, title, **changes):
        return Bien.objects.create(**{
            "agence": agency, "proprietaire": agency.owner, "titre": title,
            "ville": "Douala", "quartier": "Bonapriso", "prix": 250000,
            "description": "Un appartement avec deux chambres et une cuisine équipée.",
            "statut": StatutBien.PUBLIE, "nombre_chambres": 2, **changes,
        })

    def reply(self, phrase, *, sender="237699000064", media_id=None):
        self.sequence += 1
        inbound = {"id": f"estate-in-{self.sequence}", "from": sender, "type": "text", "text": {"body": phrase}}
        if media_id:
            inbound.update(type="audio", audio={"id": media_id})
        _, message, _ = _save_inbound(self.connection, inbound, "", timezone.now())
        with patch("whatsapp_commerce.inbox._request_meta", return_value={
            "messages": [{"id": f"estate-out-{self.sequence}"}],
        }) as meta:
            self.assertTrue(process_reply_job(message.reply_job.pk))
        return meta.call_args.kwargs["payload"]["text"]["body"] if meta.called else ""

    def test_inventory_is_scoped_to_linked_available_properties_and_remembers_budget(self):
        self.assertEqual(configuration_blockers(self.activation), [])
        self.assertIn("biens", activation_question(self.activation))
        reply = self.reply("Je cherche un appartement à Bonapriso, avec deux chambres, jusqu’à 300 000 F CFA par mois")
        self.assertIn(self.target.titre, reply)
        for excluded in ("autre agence", "tiers", "vendu", "futur", "journalier"):
            self.assertNotIn(excluded, reply)
        self.assertIn("Aucun bien", self.reply("Budget 200 000 XAF"))
        self.assertIn("n’est plus proposé par cette agence", self.reply(f"BIEN {self.another.biens_agence.first().pk}"))
        self.assertIn(self.target.titre, self.reply("NOUVELLE RECHERCHE"))
        self.assertIn(self.target.get_absolute_url(), self.reply(f"Bonjour, je regarde le BIEN {self.target.pk}."))
        self.assertIn("250", self.reply("C’est combien ?"))

    @override_settings(WHATSAPP_INBOUND_VOICE_ENABLED=True, OPENAI_API_KEY="fake-key")
    def test_visit_rechecks_inventory_and_requires_written_confirmation(self):
        salon = Salon.objects.create(owner=self.owner, name="Agenda des visites", city="Douala", whatsapp_number="237699000063")
        self.activation.booking_service = Service.objects.create(salon=salon, name="Visite", duration_minutes=60, price=0)
        self.activation.voice_enabled = True
        self.activation.save(update_fields=["booking_service", "voice_enabled"])
        day = timezone.localdate() + timedelta(days=1)
        OpeningHour.objects.create(salon=salon, weekday=day.weekday(), start_time=time(9), end_time=time(16))
        self.assertIn("Choisis d’abord", self.reply(f"RDV {day} 09:00"))
        self.reply(f"BIEN {self.target.pk}")
        command = f"RDV {day} 09:00"
        with patch("whatsapp_commerce.voice.transcribe_voice", return_value=command):
            self.assertIn(command, self.reply("", media_id="98765"))
        self.assertFalse(BusinessWhatsAppBooking.objects.exists())
        self.assertIn("Visite confirmée", self.reply(command))
        self.assertIn("Visite confirmée", self.reply(command))
        booking = BusinessWhatsAppBooking.objects.get()
        self.assertEqual(booking.property_visit.bien, self.target)
        self.assertEqual(DemandeVisite.objects.get(bien=self.target).statut, StatutVisite.CONFIRME)
        self.assertIn("Visite reportée", self.reply(f"REPORTER {booking.appointment_id} {day} 11:00"))
        booking.refresh_from_db()
        self.assertEqual(booking.appointment.time, time(11))
        self.assertIn("11:00", booking.property_visit.message)
        Bien.objects.filter(pk=self.target.pk).update(statut=StatutBien.RESERVE)
        self.assertIn("n’est plus proposé", self.reply(f"REPORTER {booking.appointment_id} {day} 13:00"))

    def test_storefront_sale_page_and_contact_link(self):
        items = collect_business_items(self.agency)
        self.assertIn(self.target.titre, [item["title"] for item in items])
        self.assertNotIn("Appartement tiers", [item["title"] for item in items])
        page = self.client.get(reverse("immobilier:offres_agences"))
        self.assertContains(page, "De la première question à la visite confirmée")
        self.assertContains(page, self.target.titre)
        self.assertNotContains(page, "Appartement vendu")
        response = self.client.get(reverse("immobilier:whatsapp_bien", args=[self.target.slug]), {"source": "profile"})
        self.assertIn("https://wa.me/237699000063", response.url)
        self.assertIn(f"BIEN+{self.target.pk}", response.url)
        self.assertTrue(BusinessLeadEvent.objects.filter(business=self.agency, source="profile", event_type="whatsapp").exists())

    def test_owner_can_edit_existing_listing_and_only_select_owned_agencies(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("immobilier:modifier_bien", args=[self.target.slug]))
        self.assertContains(response, "Modifier le bien")
        options = BienForm(instance=self.target, user=self.owner).fields["agence"].queryset
        self.assertSetEqual(set(options), {self.agency, self.another})
