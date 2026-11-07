from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from .models import Bien, StatutBien
from .models_whatsapp_draft import WhatsappImmoDraft
from .services.whatsapp_parser import improve_description, parse_immo_text


class WhatsAppImmoParserTests(TestCase):
    def test_parser_does_not_invent_location_transaction_type_or_price(self):
        parsed = parse_immo_text("Annonce disponible. Contact 699123456")

        self.assertIsNone(parsed["prix"])
        self.assertEqual(parsed["ville"], "")
        self.assertEqual(parsed["type_transaction"], "")
        self.assertEqual(parsed["type_bien"], "")

    def test_parser_extracts_explicit_offer_without_treating_phone_as_price(self):
        parsed = parse_immo_text(
            "Studio à louer à Bastos, 150 000 FCFA par mois. Contact 699123456"
        )

        self.assertEqual(parsed["prix"], 150000)
        self.assertEqual(parsed["ville"], "Yaoundé")
        self.assertEqual(parsed["quartier"], "Bastos")
        self.assertEqual(parsed["type_bien"], "STUDIO")
        self.assertEqual(parsed["type_transaction"], "LOCATION")

    def test_description_only_repeats_source_facts_and_hides_phone_number(self):
        text = "Studio à louer à Bastos, 150 000 FCFA. Contact 699123456"
        parsed = parse_immo_text(text)

        description = improve_description(text, parsed)

        self.assertIn("150 000 XAF / mois", description)
        self.assertIn("[contact à confirmer]", description)
        self.assertNotIn("699123456", description)
        self.assertNotIn("sécurisé", description.lower())
        self.assertNotIn("garanti", description.lower())


class WhatsAppImmoIngestionAndPublicationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="immo-admin",
            email="immo-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.draft = WhatsappImmoDraft.objects.create(
            raw_text="Appartement à louer à Bastos, 150 000 FCFA par mois.",
            parsed_titre="Appartement à louer à Bastos",
            parsed_type_bien="APPARTEMENT_NON_MEUBLE",
            parsed_type_transaction="LOCATION",
            parsed_prix=150000,
            parsed_ville="Yaoundé",
            parsed_quartier="Bastos",
            parsed_description="Appartement à louer à Bastos.",
            ai_improved_description="Appartement à louer à Bastos.",
            details_reviewed_at=timezone.now(),
            details_reviewed_by=self.user,
            created_by=self.user,
        )

    @override_settings(INTERNAL_WHATSAPP_SECRET="")
    def test_internal_ingest_rejects_requests_when_secret_is_not_configured(self):
        response = self.client.post(
            reverse("immobilier:internal_whatsapp_ingest"),
            data="{}",
            content_type="application/json",
            HTTP_X_INTERNAL_SECRET="anything",
        )

        self.assertEqual(response.status_code, 503)

    @override_settings(INTERNAL_WHATSAPP_SECRET="a" * 32)
    def test_internal_ingest_rejects_requests_without_valid_header_secret(self):
        response = self.client.post(
            reverse("immobilier:internal_whatsapp_ingest"),
            data="{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(INTERNAL_WHATSAPP_SECRET="a" * 32)
    def test_internal_ingest_creates_a_pending_draft_without_publishing(self):
        response = self.client.post(
            reverse("immobilier:internal_whatsapp_ingest"),
            data={
                "raw_text": "Studio à louer à Bastos, 150 000 FCFA par mois. Contact 699123456",
                "source_name": "Agent immobilier",
                "source_phone": "+237699123456",
                "whatsapp_group_name": "E-Shelle Immobilier",
            },
            content_type="application/json",
            HTTP_X_INTERNAL_SECRET="a" * 32,
        )

        self.assertEqual(response.status_code, 200)
        draft = WhatsappImmoDraft.objects.get(uuid=response.json()["draft_uuid"])
        self.assertEqual(draft.status, WhatsappImmoDraft.Status.PENDING)
        self.assertEqual(draft.parsed_prix, 150000)
        self.assertFalse(Bien.objects.exists())

    @patch(
        "immobilier_cameroun.views.whatsapp_import.publier_bien_sur_facebook",
        return_value="facebook-post-1",
    )
    def test_staff_must_confirm_republication_before_site_and_facebook_publish(self, publish):
        response = self.client.post(
            reverse(
                "immobilier:valider_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
            {},
        )

        self.assertRedirects(
            response,
            reverse(
                "immobilier:modifier_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
        )
        self.assertFalse(Bien.objects.exists())
        publish.assert_not_called()

    @patch(
        "immobilier_cameroun.views.whatsapp_import.publier_bien_sur_facebook",
        return_value="facebook-post-1",
    )
    def test_authorized_complete_draft_publishes_and_records_approver(self, publish):
        response = self.client.post(
            reverse(
                "immobilier:valider_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
            {"confirm_republishing": "on"},
        )

        self.assertRedirects(response, reverse("immobilier:whatsapp_drafts"))
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, WhatsappImmoDraft.Status.APPROVED)
        self.assertEqual(self.draft.republishing_authorized_by, self.user)
        self.assertIsNotNone(self.draft.republishing_authorized_at)
        self.assertEqual(self.draft.created_bien.statut, StatutBien.PUBLIE)
        self.assertEqual(self.draft.facebook_post_id, "facebook-post-1")
        publish.assert_called_once()

    @patch(
        "immobilier_cameroun.views.whatsapp_import.publier_bien_sur_facebook",
        return_value="facebook-post-1",
    )
    def test_incomplete_draft_cannot_publish(self, publish):
        self.draft.parsed_prix = None
        self.draft.save(update_fields=["parsed_prix"])

        response = self.client.post(
            reverse(
                "immobilier:valider_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
            {"confirm_republishing": "on"},
        )

        self.assertRedirects(
            response,
            reverse(
                "immobilier:modifier_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
        )
        self.assertFalse(Bien.objects.exists())
        publish.assert_not_called()

    @patch(
        "immobilier_cameroun.views.whatsapp_import.publier_bien_sur_facebook",
        return_value="facebook-post-1",
    )
    def test_draft_requires_manual_details_review(self, publish):
        self.draft.details_reviewed_at = None
        self.draft.details_reviewed_by = None
        self.draft.save(update_fields=["details_reviewed_at", "details_reviewed_by"])

        response = self.client.post(
            reverse(
                "immobilier:valider_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
            {"confirm_republishing": "on"},
        )

        self.assertRedirects(
            response,
            reverse(
                "immobilier:modifier_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
        )
        self.assertFalse(Bien.objects.exists())
        publish.assert_not_called()

    def test_staff_can_save_corrected_details_and_record_the_review(self):
        response = self.client.post(
            reverse(
                "immobilier:modifier_whatsapp_draft",
                kwargs={"draft_uuid": self.draft.uuid},
            ),
            {
                "titre": "Studio vérifié à Bastos",
                "type_bien": "STUDIO",
                "type_transaction": "LOCATION",
                "ville": "Yaoundé",
                "quartier": "Bastos",
                "prix": "175000",
                "conditions": "2 mois d'avance",
                "source_name": "Agent immobilier",
                "source_phone": "+237699123456",
                "description": "Studio à louer à Bastos.",
                "confirm_details_reviewed": "on",
            },
        )

        self.assertRedirects(response, reverse("immobilier:whatsapp_drafts"))
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.parsed_type_bien, "STUDIO")
        self.assertEqual(self.draft.parsed_prix, 175000)
        self.assertEqual(self.draft.details_reviewed_by, self.user)
        self.assertIsNotNone(self.draft.details_reviewed_at)

# Create your tests here.
