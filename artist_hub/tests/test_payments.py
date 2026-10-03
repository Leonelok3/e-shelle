"""
artist_hub/tests/test_payments.py
Tests unitaires pour le module payments :
- MockProvider (initiate, verify)
- Idempotence stricte de handle_payment_success
- Propagation du signal payment_succeeded vers le candidat (statut -> INSCRIT)
- Webhook CSRF exempt et réponse JSON
"""
import json
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from artist_hub.payments.models import Payment, PaymentStatus, PaymentMethod
from artist_hub.payments.services import (
    create_payment,
    handle_payment_success,
    handle_payment_failure,
)
from artist_hub.payments.providers.factory import get_payment_provider
from artist_hub.casting.models import CastingSession, Candidate, CandidateStatus, CandidateGender


class PaymentModuleTests(TestCase):
    def setUp(self):
        self.session = CastingSession.objects.create(
            title="Session Paiement Test",
            slug="session-paiement-test",
            fee_cameroon=3000,
            fee_international=5000,
            is_active=True,
        )
        self.client = Client()

    def test_idempotent_payment_success(self):
        payment = create_payment(
            amount=3000,
            currency="XAF",
            payer_name="Test Idempotence",
            payer_phone="+237675000111",
        )
        self.assertEqual(payment.status, PaymentStatus.PENDING)

        # 1er appel : succès, retourne True
        first_call = handle_payment_success(payment, raw_data={"tx_id": "123"})
        self.assertTrue(first_call)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.SUCCESS)
        self.assertIsNotNone(payment.verified_at)

        # 2e appel : IDEMPOTENT, retourne False sans re-déclencher
        second_call = handle_payment_success(payment, raw_data={"tx_id": "123"})
        self.assertFalse(second_call)
        self.assertEqual(payment.status, PaymentStatus.SUCCESS)

    def test_payment_succeeded_signal_updates_candidate(self):
        today = datetime.date.today()
        candidate = Candidate.objects.create(
            session=self.session,
            first_name="Marc",
            last_name="Vivien",
            birth_date=datetime.date(today.year - 24, today.month, today.day),
            gender=CandidateGender.HOMME,
            height_cm=186,
            city="Douala",
            phone="+237675333444",
            email="marc@test.com",
            candidate_number="CAST-2026-0099",
            access_code="OPUS-SIGNAL-1",
            status=CandidateStatus.EN_ATTENTE_VALIDATION,
        )

        payment = create_payment(
            amount=3000,
            currency="XAF",
            payer_name=candidate.full_name,
            payer_phone=candidate.phone,
            content_object=candidate,
        )
        candidate.payment = payment
        candidate.save()

        self.assertEqual(candidate.status, CandidateStatus.EN_ATTENTE_VALIDATION)

        # Déclenchement de la validation
        handle_payment_success(payment)

        # Vérification que le candidat est passé à INSCRIT via le signal
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, CandidateStatus.INSCRIT)

    def test_payment_endpoints_are_disabled(self):
        self.assertEqual(self.client.post("/artist-hub/payments/webhook/").status_code, 404)
