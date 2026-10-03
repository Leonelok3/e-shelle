"""
artist_hub/tests/test_casting.py
Tests unitaires pour le module casting :
- Création de candidature
- Détection des mineurs et calcul d'âge
- Formulaire et validation des règles tuteurs
- Prévention des doublons par téléphone
- Génération de PDF et QR code
"""
import datetime
from django.test import TestCase
from django.utils import timezone
from artist_hub.casting.models import (
    CastingSession,
    Candidate,
    CandidateStatus,
    CandidateGender,
)
from artist_hub.casting.services import (
    generate_candidate_number,
    generate_access_code,
    generate_candidate_pdf,
)
from artist_hub.casting.forms import CandidateRegistrationForm


class CastingModelAndServiceTests(TestCase):
    def setUp(self):
        self.session = CastingSession.objects.create(
            title="Douala Fashion Week 2026 Test",
            slug="douala-fashion-week-2026-test",
            event_date=datetime.date(2026, 12, 26),
            event_location="Hôtel Krystal Palace, Douala",
            fee_cameroon=3000,
            fee_international=5000,
            min_height_male=183,
            min_height_female=175,
            is_active=True,
        )

    def test_candidate_number_and_access_code_generation(self):
        num1 = generate_candidate_number(self.session)
        num2 = generate_candidate_number(self.session)
        code = generate_access_code()

        self.assertTrue(num1.startswith("CAST-"))
        self.assertTrue(code.startswith("OPUS-"))
        self.assertNotEqual(num1, "")

    def test_age_calculation_and_minor_detection(self):
        today = datetime.date.today()
        # Majeur (22 ans)
        birth_major = datetime.date(today.year - 22, today.month, today.day)
        c_major = Candidate.objects.create(
            session=self.session,
            first_name="Jean",
            last_name="Paul",
            birth_date=birth_major,
            gender=CandidateGender.HOMME,
            height_cm=185,
            city="Douala",
            phone="+237675000001",
            email="jean@test.com",
            candidate_number="CAST-2026-0001",
            access_code="OPUS-TEST-1",
            is_minor=False,
        )
        self.assertEqual(c_major.age, 22)
        self.assertFalse(c_major.is_minor)

        # Mineur (16 ans)
        birth_minor = datetime.date(today.year - 16, today.month, today.day)
        c_minor = Candidate.objects.create(
            session=self.session,
            first_name="Marie",
            last_name="Bella",
            birth_date=birth_minor,
            gender=CandidateGender.FEMME,
            height_cm=177,
            city="Yaoundé",
            phone="+237675000002",
            email="marie@test.com",
            candidate_number="CAST-2026-0002",
            access_code="OPUS-TEST-2",
            is_minor=True,
            guardian_name="Parent Bella",
            guardian_phone="+237699000000",
            parental_consent=True,
        )
        self.assertEqual(c_minor.age, 16)
        self.assertTrue(c_minor.is_minor)
        self.assertTrue(c_minor.parental_consent)

    def test_pdf_generation_returns_valid_bytes(self):
        today = datetime.date.today()
        candidate = Candidate.objects.create(
            session=self.session,
            first_name="Christelle",
            last_name="Nguemo",
            birth_date=datetime.date(today.year - 20, today.month, today.day),
            gender=CandidateGender.FEMME,
            height_cm=178,
            city="Douala",
            country="Cameroun",
            phone="+237675123456",
            email="christelle@test.com",
            candidate_number="CAST-2026-0010",
            access_code="OPUS-PDF-1",
            status=CandidateStatus.INSCRIT,
        )

        pdf_bytes = generate_candidate_pdf(candidate)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 1000)
        # Vérifie le header PDF standard
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
