from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from artist_hub.models import CastingSession, Candidate, Payment


def photo(name):
    stream = BytesIO()
    Image.new("RGB", (100, 150), "white").save(stream, "JPEG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/jpeg")


class FreeRegistrationTests(TestCase):
    def setUp(self):
        self.session = CastingSession.objects.create(title="Casting gratuit", slug="free", is_active=True)

    def test_registration_without_payment_and_staff_selection(self):
        response = self.client.post(reverse("artist_hub:casting:register"), {
            "first_name": "Marie", "last_name": "Test", "birth_date": "2000-01-01",
            "gender": "F", "height_cm": 178, "city": "Douala", "country": "Cameroun",
            "phone": "+237600000001", "email": "test@example.com",
            "video_url": "https://example.com/video", "gdpr_consent": "on",
            "selection_disclaimer_accepted": "on", "photo_portrait": photo("portrait.jpg"),
            "photo_full_length": photo("full.jpg"),
        })
        self.assertRedirects(response, reverse("artist_hub:casting:confirmation"))
        candidate = Candidate.objects.get()
        self.assertEqual(candidate.status, "INSCRIT")
        self.assertIsNone(candidate.payment_id)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(candidate.photos.count(), 2)
        confirmation = self.client.get(reverse("artist_hub:casting:confirmation"))
        self.assertContains(confirmation, candidate.candidate_number)
        from artist_hub.casting.views_dashboard import set_candidate_status
        set_candidate_status(candidate, "RETENU")
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "RETENU")

    def test_public_pages_do_not_request_payment(self):
        for name in ("index", "register", "track"):
            response = self.client.get(reverse("artist_hub:casting:" + name))
            self.assertEqual(response.status_code, 200)
            for token in ("FCFA", "XAF", "Ecobank", "Orange Money", "payment_method", "proof_file"):
                self.assertNotContains(response, token)

    def test_existing_pending_dossiers_are_unblocked_without_changing_jury_decisions(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        for index, status in enumerate(("EN_ATTENTE_PAIEMENT", "EN_ATTENTE_VALIDATION", "RETENU", "REFUSE")):
            Candidate.objects.create(session=self.session, first_name="Test", last_name="Migration",
                birth_date="2000-01-01", gender="F", height_cm=178, city="Douala",
                phone=str(index), email="test@example.com", candidate_number=f"CAST-{index}",
                access_code=f"CODE-{index}", status=status)
        from types import SimpleNamespace
        import_module("artist_hub.migrations.0004_free_casting").make_casting_free(apps, SimpleNamespace(connection=connection))
        self.assertEqual(Candidate.objects.filter(status="INSCRIT").count(), 2)
        self.assertEqual(Candidate.objects.filter(status="RETENU").count(), 1)
        self.assertEqual(Candidate.objects.filter(status="REFUSE").count(), 1)
        self.session.refresh_from_db()
        self.assertEqual(self.session.fee_cameroon, 0)
