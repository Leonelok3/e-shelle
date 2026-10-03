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

    def test_mock_provider_initiate_and_verify(self):
        payment = create_payment(
            amount=3000,
            currency="XAF",
            payer_name="Samuel Eto'o",
            payer_phone="+237675999888",
            provider_name="mock",
        )
        self.assertTrue(payment.reference.startswith("PAY-"))
        self.assertEqual(payment.status, PaymentStatus.PENDING)

        provider = get_payment_provider("mock")
        res_init = provider.initiate(payment)
        self.assertTrue(res_init.success)
        self.assertIn(payment.reference, res_init.payment_url)

        # Avant validation : is_paid = False
        res_verify_before = provider.verify(payment.reference)
        self.assertFalse(res_verify_before.is_paid)

        # Après validation
        payment.status = PaymentStatus.SUCCESS
        payment.save()
        res_verify_after = provider.verify(payment.reference)
        self.assertTrue(res_verify_after.is_paid)

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

    def test_webhook_csrf_exempt_and_idempotence(self):
        payment = create_payment(
            amount=5000,
            currency="XAF",
            payer_name="Client Webhook",
            payer_phone="+237699111222",
            provider_name="mock",
        )

        url = reverse("artist_hub:payments:webhook")
        payload = json.dumps({"reference": payment.reference, "status": "SUCCESS"})

        # Appel POST sans token CSRF
        response = self.client.post(
            url,
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Le deuxième appel identique doit également retourner 200 de façon idempotente
        response2 = self.client.post(
            url,
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 200)
