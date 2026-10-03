"""
artist_hub/tests/test_dashboard.py
Tests unitaires pour le dashboard staff et les permissions de sécurité :
- Contrôle d'accès strict UserPassesTestMixin (is_staff obligatoire)
- Affichage de la liste des candidats et KPIs
- Validation manuelle d'un versement par le staff
- Export CSV avec encodage UTF-8 et en-têtes
"""
import datetime
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from artist_hub.casting.models import (
    CastingSession,
    Candidate,
    CandidateStatus,
    CandidateGender,
)
from artist_hub.payments.services import create_payment

User = get_user_model()


class StaffDashboardSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.session = CastingSession.objects.create(
            title="Session Staff Test",
            slug="session-staff-test",
            fee_cameroon=3000,
            fee_international=5000,
            is_active=True,
        )

        # Utilisateur normal (non staff)
        self.normal_user = User.objects.create_user(
            username="normal_user",
            password="Password123!",
            email="normal@test.com",
        )

        # Utilisateur staff
        self.staff_user = User.objects.create_user(
            username="staff_user",
            password="Password123!",
            email="staff@test.com",
            is_staff=True,
        )

        # Candidat de test
        today = datetime.date.today()
        self.candidate = Candidate.objects.create(
            session=self.session,
            first_name="Boris",
            last_name="Tchoupo",
            birth_date=datetime.date(today.year - 23, today.month, today.day),
            gender=CandidateGender.HOMME,
            height_cm=187,
            city="Douala",
            phone="+237675777888",
            email="boris@test.com",
            candidate_number="CAST-2026-0777",
            access_code="OPUS-STAFF-1",
            status=CandidateStatus.EN_ATTENTE_VALIDATION,
        )
        self.payment = create_payment(
            amount=3000,
            currency="XAF",
            payer_name=self.candidate.full_name,
            payer_phone=self.candidate.phone,
            content_object=self.candidate,
            provider_name="manual_proof",
        )
        self.payment.external_reference = "STAFF-TEST-VERSEMENT"
        self.payment.save(update_fields=["external_reference"])
        self.candidate.payment = self.payment
        self.candidate.save()

    def test_anonymous_user_redirected(self):
        url = reverse("artist_hub:casting:dashboard")
        response = self.client.get(url)
        # Redirection vers la page de login admin
        self.assertEqual(response.status_code, 302)

    def test_normal_user_denied_access(self):
        self.client.login(username="normal_user", password="Password123!")
        url = reverse("artist_hub:casting:dashboard")
        response = self.client.get(url)
        # Refusé et redirigé
        self.assertEqual(response.status_code, 302)

    def test_staff_user_granted_access(self):
        self.client.login(username="staff_user", password="Password123!")
        url = reverse("artist_hub:casting:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Boris Tchoupo")
        self.assertContains(response, "CAST-2026-0777")

    def test_staff_can_validate_candidate_payment(self):
        self.client.login(username="staff_user", password="Password123!")
        url = reverse(
            "artist_hub:casting:staff_candidate_detail",
            kwargs={"candidate_number": self.candidate.candidate_number},
        )
        response = self.client.post(url, data={"action": "validate_payment"})
        self.assertEqual(response.status_code, 302)

        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, CandidateStatus.INSCRIT)
        self.candidate.payment.refresh_from_db()
        self.assertTrue(self.candidate.payment.is_successful)

    def test_staff_export_csv(self):
        self.client.login(username="staff_user", password="Password123!")
        url = reverse("artist_hub:casting:staff_export_csv")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment", response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("CAST-2026-0777", content)
        self.assertIn("Tchoupo", content)
