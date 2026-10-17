import json
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessLeadEvent, BusinessProfile
from business.services import (
    create_lead_from_event,
    generate_campaign_links,
    get_audience_for_campaign,
    handle_ai_phone_capture,
)
from whatsapp_agent.models import CampaignLinkClick, Campagne, ContactWhatsApp, MessageEnvoi
from whatsapp_agent.views import _creer_messages_campagne
from whatsapp_commerce.models import BusinessWhatsAppContact


TEST_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path(__file__).resolve().parent.parent / "templates"],
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.locmem.Loader",
                    {
                        "base.html": "{% block content %}{% endblock %}",
                        "partials/whatsapp_nav.html": "",
                    },
                ),
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ]
        },
    }
]


@override_settings(TEMPLATES=TEST_TEMPLATES)
class BusinessCampaignTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="business-owner")
        self.other_owner = user_model.objects.create_user(username="other-owner")
        self.staff = user_model.objects.create_user(username="campaign-staff", is_staff=True)
        self.business = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.RESTO,
            name="Le Boj",
            city="Douala",
            phone="699000099",
            whatsapp="+237680625082",
        )

    def create_event(self, interest="restaurant"):
        return BusinessLeadEvent.objects.create(
            business=self.business,
            event_type=BusinessLeadEvent.EventType.WHATSAPP,
            source="business_profile",
            metadata={"city": "Douala", "interest": interest},
        )

    @override_settings(WHATSAPP_COMMERCE_ENABLED=False)
    def test_business_campaign_launch_explains_feature_is_not_enabled(self):
        campaign = Campagne.objects.create(
            nom="Promo Le Boj",
            business=self.business,
            message_template="Promotion",
            statut=Campagne.STATUT_VALIDEE,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("whatsapp_agent:wa_lancer", args=[campaign.pk]),
            {"confirm_launch": "on"},
        )

        campaign.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(campaign.statut, Campagne.STATUT_VALIDEE)
        self.assertIn(
            "Fonction Business en activation, contactez le support.",
            [str(message) for message in get_messages(response.wsgi_request)],
        )

    @override_settings(WHATSAPP_COMMERCE_ENABLED=True)
    def test_business_campaign_without_prepared_recipients_is_not_launched(self):
        campaign = Campagne.objects.create(
            nom="Promo Le Boj",
            business=self.business,
            message_template="Promotion",
            statut=Campagne.STATUT_VALIDEE,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("whatsapp_agent:wa_lancer", args=[campaign.pk]),
            {"confirm_launch": "on"},
        )

        campaign.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(campaign.statut, Campagne.STATUT_VALIDEE)
        self.assertIn(
            "Aucun destinataire consentant n'est prepare pour cette campagne.",
            [str(message) for message in get_messages(response.wsgi_request)],
        )

    def create_opted_in_contact(self, phone="+237699000001", tags=None):
        return BusinessWhatsAppContact.objects.create(
            business=self.business,
            phone=phone,
            marketing_opt_in=True,
            consent_marketing=True,
            consent_source="business_profile",
            tags=tags or ["Douala", "restaurant Akwa"],
        )

    def test_public_profile_shows_service_and_optional_marketing_consent(self):
        response = self.client.get(
            reverse("business:public_profile", kwargs={"public_slug": self.business.public_slug})
        )

        self.assertContains(response, 'name="consent_service"')
        self.assertContains(response, 'name="consent_marketing"')
        self.assertContains(response, 'name="phone"')
        self.assertContains(response, "STOP")
        self.assertContains(response, "required checked")

    def test_whatsapp_consent_is_saved_and_redirects_to_the_existing_target(self):
        profile = self.client.get(
            reverse("business:public_profile", kwargs={"public_slug": self.business.public_slug})
        )
        existing_target = profile.context["whatsapp_url"]
        response = self.client.post(
            reverse("business:whatsapp_consent", kwargs={"public_slug": self.business.public_slug}),
            {
                "phone": "699 000 001",
                "consent_service": "on",
                "consent_marketing": "on",
            },
        )

        contact = ContactWhatsApp.objects.get(numero="+237699000001")
        self.assertRedirects(response, existing_target, fetch_redirect_response=False)
        self.assertTrue(contact.consent_service)
        self.assertTrue(contact.consent_marketing)
        self.assertEqual(contact.consent_entity, self.business)
        self.assertIsNotNone(contact.consent_date)
        self.assertIn(self.business.get_absolute_url(), contact.consent_source)

    def test_missing_service_consent_does_not_save_contact(self):
        response = self.client.post(
            reverse("business:whatsapp_consent", kwargs={"public_slug": self.business.public_slug}),
            {"phone": "699000001"},
        )

        self.assertRedirects(
            response,
            reverse("business:public_profile", kwargs={"public_slug": self.business.public_slug}),
            fetch_redirect_response=False,
        )
        self.assertFalse(ContactWhatsApp.objects.exists())
        self.assertIn(
            "Vous devez accepter pour être recontacté pour votre commande",
            [str(message) for message in get_messages(response.wsgi_request)],
        )

    def test_updating_contact_preserves_legacy_campaign_and_unsubscribe_fields(self):
        existing = ContactWhatsApp.objects.create(
            numero="+237699000001",
            consentement_confirme=True,
            desinscrit=True,
            note="Historique des campagnes précédentes",
        )

        self.client.post(
            reverse("business:whatsapp_consent", kwargs={"public_slug": self.business.public_slug}),
            {
                "phone": "699000001",
                "consent_service": "on",
            },
        )

        existing.refresh_from_db()
        self.assertTrue(existing.consentement_confirme)
        self.assertTrue(existing.desinscrit)
        self.assertEqual(existing.note, "Historique des campagnes précédentes")
        self.assertFalse(existing.consent_marketing)
        self.assertTrue(existing.consent_service)

    def test_lead_bridge_creates_business_and_global_contacts_with_consent(self):
        event = self.create_event("restaurant Akwa")

        business_contact, global_contact = create_lead_from_event(event, "699000001")

        self.assertEqual(business_contact.phone, "+237699000001")
        self.assertEqual(business_contact.tags, ["Douala", "restaurant Akwa"])
        self.assertTrue(business_contact.marketing_opt_in)
        self.assertTrue(global_contact.consentement_confirme)
        self.assertEqual(global_contact.ville, "Douala")
        self.assertEqual(ContactWhatsApp.objects.count(), 1)
        self.assertEqual(BusinessLeadEvent.objects.count(), 1)

    def test_lead_bridge_updates_existing_tags_without_recreating_contact(self):
        existing, _ = create_lead_from_event(self.create_event("restaurant"), "699000001")

        updated, global_contact = create_lead_from_event(self.create_event("poulet braise"), "+237 699 000 001")

        self.assertEqual(updated.pk, existing.pk)
        self.assertEqual(updated.tags, ["Douala", "restaurant", "poulet braise"])
        self.assertTrue(global_contact.consentement_confirme)
        self.assertEqual(BusinessWhatsAppContact.objects.count(), 1)

    def test_global_unsubscribe_is_preserved_in_business_crm(self):
        global_contact = ContactWhatsApp.objects.create(
            numero="+237699000001",
            consentement_confirme=False,
            desinscrit=True,
            desinscrit_le=timezone.now(),
        )

        business_contact, returned_global_contact = create_lead_from_event(
            self.create_event(),
            global_contact.numero,
        )

        self.assertEqual(returned_global_contact.pk, global_contact.pk)
        self.assertFalse(business_contact.marketing_opt_in)
        self.assertFalse(business_contact.consent_marketing)
        self.assertIsNotNone(business_contact.opted_out_at)

    def test_owner_only_creates_campaigns_for_owned_business(self):
        other_business = BusinessProfile.objects.create(
            owner=self.other_owner,
            module=BusinessProfile.Module.RESTO,
            name="Other restaurant",
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("business_whatsapp_campaigns"),
            {
                "nom": "Promo Ndolé",
                "business": other_business.pk,
                "message_template": "Bonjour {{1}}, promo Ndolé !",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Campagne.objects.exists())

        response = self.client.post(
            reverse("business_whatsapp_campaigns"),
            {
                "nom": "Promo Ndolé",
                "business": self.business.pk,
                "filtre_ville": "Douala",
                "audience_interest": "restaurant",
                "message_template": "Bonjour {{1}}, promo Ndolé !",
            },
        )

        campaign = Campagne.objects.get()
        self.assertRedirects(response, reverse("business_whatsapp_campaigns"))
        self.assertEqual(campaign.business, self.business)
        self.assertEqual(campaign.statut, Campagne.STATUT_BROUILLON)
        self.assertEqual(campaign.total_destinataires, 0)
        self.assertFalse(campaign.messages.exists())

    def test_owner_campaign_creates_tracked_links_and_shows_personalized_example(self):
        contact = self.create_opted_in_contact()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("business_whatsapp_campaigns"),
            {
                "nom": "Promo Ndolé",
                "business": self.business.pk,
                "filtre_ville": "Douala",
                "audience_interest": "restaurant",
                "message_template": "Bonjour {{prenom}}, Ndolé disponible !",
            },
        )

        campaign = Campagne.objects.get()
        link = CampaignLinkClick.objects.get(campaign=campaign, contact=contact)
        self.assertRedirects(response, reverse("business_whatsapp_campaigns"))
        self.assertEqual(campaign.total_destinataires, 1)

        response = self.client.get(reverse("business_whatsapp_campaigns"))

        self.assertContains(response, f"Bonjour {contact.phone}, Ndolé disponible !")
        self.assertContains(response, f"https://e-shelle.com/r/{link.short_code}/")

    def test_business_audience_preview_is_owner_scoped_and_requires_marketing_consent(self):
        self.create_opted_in_contact()
        self.create_opted_in_contact(phone="+237699000002", tags=["Douala", "restaurant Bonamoussadi"])
        BusinessWhatsAppContact.objects.create(
            business=self.business,
            phone="+237699000003",
            tags=["Douala", "restaurant Akwa"],
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("whatsapp_agent:wa_business_campaign_audience"),
            data=json.dumps(
                {
                    "business_id": self.business.pk,
                    "city": "Douala",
                    "interest": "restaurant Akwa",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["business"], self.business.display_name)

    def test_staff_audience_preview_uses_global_consent_across_businesses(self):
        restaurant = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.RESTO,
            name="RICO'S KITCHIN",
            city="Douala",
        )
        pressing = BusinessProfile.objects.create(
            owner=self.other_owner,
            module=BusinessProfile.Module.PRESSING,
            name="Pressing Test",
            city="Douala",
        )
        global_contacts = []
        for phone, name in [
            ("+237699000002", "Paul"),
            ("+237699000004", "Marie"),
            ("+237699000005", "Jacques"),
        ]:
            global_contacts.append(
                BusinessWhatsAppContact.objects.create(
                    business=pressing,
                    phone=phone,
                    display_name=name,
                    marketing_opt_in=True,
                    consent_marketing=True,
                    custom_fields={"city": "Douala, Cameroon"},
                    tags=["restaurant", "Akwa", "pressing"],
                )
            )
        BusinessWhatsAppContact.objects.create(
            business=pressing,
            phone="+237699000003",
            marketing_opt_in=True,
            consent_marketing=False,
            custom_fields={"city": "Douala, Cameroon"},
            tags=["restaurant", "Akwa", "pressing"],
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("whatsapp_agent:wa_business_campaign_audience"),
            data=json.dumps(
                {
                    "business_id": restaurant.pk,
                    "city": "Douala",
                    "interest": "restaurant",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 3)
        self.assertTrue(response.json()["global_audience"])
        self.assertIn("MODE E-SHELLE ADMIN", response.json()["audience_message"])
        self.assertSetEqual(
            {example["name"] for example in response.json()["examples"]},
            {contact.display_name for contact in global_contacts},
        )

        response = self.client.post(
            reverse("whatsapp_agent:wa_business_campaign_audience"),
            data=json.dumps(
                {
                    "business_id": restaurant.pk,
                    "city": "Douala",
                    "interest": "pressing",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 3)

    def test_staff_campaign_form_explains_global_audience(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("whatsapp_agent:wa_creer"))

        self.assertContains(response, "MODE E-SHELLE ADMIN : Audience globale E-Shelle.")

    def test_staff_business_campaign_draft_counts_global_audience(self):
        restaurant = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.RESTO,
            name="RICO'S KITCHIN",
            city="Douala",
        )
        pressing = BusinessProfile.objects.create(
            owner=self.other_owner,
            module=BusinessProfile.Module.PRESSING,
            name="Pressing Test",
            city="Douala",
        )
        BusinessWhatsAppContact.objects.create(
            business=pressing,
            phone="+237699000002",
            marketing_opt_in=True,
            consent_marketing=True,
            custom_fields={"city": "Douala"},
            tags=["pressing"],
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("whatsapp_agent:wa_creer"),
            {
                "nom": "Promo RICO'S KITCHIN",
                "business": restaurant.pk,
                "filtre_ville": "Douala",
                "message_template": "Bonjour {{1}}, promo resto !",
                "action": "draft",
            },
        )

        campaign = Campagne.objects.get()
        self.assertRedirects(response, reverse("whatsapp_agent:wa_detail", args=[campaign.pk]))
        self.assertEqual(campaign.total_destinataires, 1)
        self.assertEqual(campaign.business, restaurant)

    def test_global_campaign_audience_filters_city_and_interest_across_contact_fields(self):
        restaurant = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.RESTO,
            name="RICO'S KITCHIN",
            city="Douala",
        )
        pressing = BusinessProfile.objects.create(
            owner=self.other_owner,
            module=BusinessProfile.Module.PRESSING,
            name="Pressing Test",
            city="Douala",
        )
        for phone, name in [
            ("+237699000021", "Paul"),
            ("+237699000022", "Marie"),
            ("+237699000023", "Jacques"),
        ]:
            BusinessWhatsAppContact.objects.create(
                business=pressing,
                phone=phone,
                display_name=name,
                marketing_opt_in=True,
                consent_marketing=True,
                custom_fields={"city": "Douala, Cameroon"},
                tags=["restaurant", "Akwa"],
            )

        campaign = Campagne.objects.create(
            nom="RICO'S KITCHIN - Douala",
            business=restaurant,
            message_template="Promotion restaurant",
            filtre_ville="Douala",
            audience_interest="restaurant",
            cree_par=self.staff,
        )
        audience = get_audience_for_campaign(
            campaign.business,
            campaign.filtre_ville,
            campaign.audience_interest,
            user=self.staff,
        )

        self.assertEqual(audience.count(), 3)
        self.assertSetEqual(
            set(audience.values_list("display_name", flat=True)),
            {"Paul", "Marie", "Jacques"},
        )

    def test_campaign_detail_refreshes_business_audience_count_and_final_preview(self):
        restaurant = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.RESTO,
            name="RICO'S KITCHIN",
            city="Douala",
        )
        pressing = BusinessProfile.objects.create(
            owner=self.other_owner,
            module=BusinessProfile.Module.PRESSING,
            name="Pressing Test",
            city="Douala",
        )
        for index, name in enumerate(["Paul", "Marie", "Jacques"], start=31):
            BusinessWhatsAppContact.objects.create(
                business=pressing,
                phone=f"+2376990000{index}",
                display_name=name,
                marketing_opt_in=True,
                consent_marketing=True,
                custom_fields={"city": "Douala, Cameroon"},
                tags=["restaurant", "Akwa"],
            )
        campaign = Campagne.objects.create(
            nom="RICO'S KITCHIN - Douala",
            business=restaurant,
            message_template="Promotion restaurant",
            filtre_ville="Douala",
            audience_interest="restaurant",
            cree_par=self.staff,
            total_destinataires=0,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("whatsapp_agent:wa_detail", args=[campaign.pk]))

        campaign.refresh_from_db()
        self.assertEqual(campaign.total_destinataires, 3)
        self.assertContains(response, "Destinataires prepares: <strong>3</strong>")
        self.assertContains(response, "Audience globale E-Shelle")
        self.assertContains(response, "Paul")
        self.assertContains(response, "Marie")
        self.assertContains(response, "Jacques")

    def test_campaign_messages_require_the_selected_consent_type(self):
        marketing_contact = ContactWhatsApp.objects.create(
            numero="+237699000031",
            consent_marketing=True,
        )
        service_contact = ContactWhatsApp.objects.create(
            numero="+237699000032",
            consent_service=True,
        )
        legacy_contact = ContactWhatsApp.objects.create(
            numero="+237699000033",
            consentement_confirme=True,
        )
        campaign = Campagne.objects.create(
            nom="Consentement filtre",
            message_template="Bonjour",
            filtre_role="selection_contacts",
        )
        campaign.destinataires_contacts.set(
            [marketing_contact, service_contact, legacy_contact]
        )

        with patch("whatsapp_agent.views.WhatsAppService.recuperer_contacts") as fallback:
            _creer_messages_campagne(campaign)
            self.assertEqual(
                list(campaign.messages.values_list("numero_whatsapp", flat=True)),
                [marketing_contact.numero],
            )
            fallback.assert_not_called()

            campaign.consent_type = Campagne.CONSENT_SERVICE
            campaign.save(update_fields=["consent_type"])
            _creer_messages_campagne(campaign)

        self.assertEqual(
            list(campaign.messages.values_list("numero_whatsapp", flat=True)),
            [service_contact.numero],
        )
        self.assertEqual(campaign.messages.count(), 1)

    def test_campaign_links_are_personal_and_filtered_to_consented_audience(self):
        contact = self.create_opted_in_contact()
        self.create_opted_in_contact(
            phone="+237699000002",
            tags=["Douala", "pressing"],
        )
        campaign = Campagne.objects.create(
            nom="Promo Ndolé",
            business=self.business,
            message_template="Bonjour {{prenom}}, promo !",
            filtre_ville="Douala",
            audience_interest="restaurant",
        )

        links = generate_campaign_links(campaign)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["phone"], contact.phone)
        self.assertRegex(links[0]["click"].short_code, r"^le-1-[a-z0-9]{4}$")
        self.assertEqual(links[0]["link"], f"https://e-shelle.com/r/{links[0]['click'].short_code}/")
        self.assertEqual(CampaignLinkClick.objects.count(), 1)
        self.assertEqual(generate_campaign_links(campaign)[0]["click"].pk, links[0]["click"].pk)

    def test_campaign_redirect_increments_count_and_records_business_event(self):
        contact = self.create_opted_in_contact()
        campaign = Campagne.objects.create(
            nom="Promo Ndolé",
            business=self.business,
            message_template="Bonjour {{1}}",
        )
        link = CampaignLinkClick.objects.create(
            campaign=campaign,
            contact=contact,
            short_code="boj13-a7k9",
        )

        response = self.client.get(reverse("campaign_redirect", kwargs={"short_code": link.short_code}))

        campaign.refresh_from_db()
        event = BusinessLeadEvent.objects.get(event_type="campaign_click")
        link.refresh_from_db()
        self.assertEqual(campaign.clicked_count, 1)
        self.assertEqual(event.business, self.business)
        self.assertEqual(event.metadata, {"campaign_id": campaign.pk, "contact_phone": contact.phone})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://wa.me/"))
        self.assertIn(f"campagne+{campaign.pk}", response["Location"])
        self.assertIsNotNone(link.ip)

    def test_ai_phone_capture_requires_affirmative_opt_in_and_business_context(self):
        self.assertIsNone(handle_ai_phone_capture("Mon numero 698123456 non pour les promos", self.business))
        reply = handle_ai_phone_capture("Mon numéro 698123456 oui pour promo", self.business)

        self.assertEqual(reply, "Parfait, j'ai bien noté 698123456 pour les promos de Le Boj.")
        contact = BusinessWhatsAppContact.objects.get(business=self.business, phone="+237698123456")
        self.assertTrue(contact.consent_marketing)
        self.assertIn("Douala", contact.tags)
        self.assertIn("restaurant", contact.tags)

    def test_ai_capture_does_not_claim_promo_opt_in_after_global_unsubscribe(self):
        ContactWhatsApp.objects.create(
            numero="+237698123456",
            desinscrit=True,
            consentement_confirme=False,
        )

        reply = handle_ai_phone_capture("Mon numero 698123456 oui pour promo", self.business)

        self.assertIn("desinscrit", reply)
        self.assertFalse(
            BusinessWhatsAppContact.objects.get(
                business=self.business,
                phone="+237698123456",
            ).marketing_opt_in
        )

    def test_chat_widget_message_with_business_id_captures_opted_in_phone(self):
        response = self.client.post(
            reverse("chat:send_message"),
            data=json.dumps(
                {
                    "message": "Mon numero 698123456 oui pour promo",
                    "business_id": self.business.pk,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("promo", response.json()["message"])
        self.assertTrue(
            BusinessWhatsAppContact.objects.filter(
                business=self.business,
                phone="+237698123456",
                consent_marketing=True,
            ).exists()
        )

    def test_staff_campaign_creation_keeps_global_campaigns_available(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("whatsapp_agent:wa_creer"),
            {
                "nom": "Global notice",
                "message_template": "Bonjour {{prenom}}",
                "action": "draft",
                "meta_template": "",
            },
        )

        self.assertRedirects(response, reverse("whatsapp_agent:wa_detail", args=[Campagne.objects.get().pk]))
        self.assertIsNone(Campagne.objects.get().business_id)
