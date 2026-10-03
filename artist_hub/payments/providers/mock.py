"""
artist_hub/payments/providers/mock.py
Connecteur de test / dev local simulant les paiements MoMo, Orange Money et Carte.
Permet d'exécuter l'intégralité du tunnel sans compte marchand actif.
"""
import json
from typing import Optional, Dict, Any
from django.urls import reverse
from django.http import HttpRequest
from .base import BasePaymentProvider, PaymentResult, PaymentVerificationResult
from artist_hub.payments.models import PaymentStatus


class MockProvider(BasePaymentProvider):
    """Fournisseur fictif pour les tests et la démonstration locale."""

    name: str = "mock"

    def initiate(self, payment, return_url: Optional[str] = None) -> PaymentResult:
        """
        Génère une URL locale de simulation de paiement.
        """
        mock_url = reverse("artist_hub:payments:mock_simulate", kwargs={"reference": payment.reference})
        return PaymentResult(
            success=True,
            payment_url=mock_url,
            reference=payment.reference,
            message="Redirection vers la simulation de paiement locale (Mock)",
            raw_data={"mode": "mock", "reference": payment.reference},
        )

    def verify(self, reference: str) -> PaymentVerificationResult:
        """Vérifie le paiement dans la base locale."""
        from artist_hub.payments.models import Payment

        payment = Payment.objects.filter(reference=reference).first()
        if not payment:
            return PaymentVerificationResult(
                is_paid=False,
                status="NOT_FOUND",
                error_message=f"Paiement {reference} introuvable",
            )

        is_paid = payment.status == PaymentStatus.SUCCESS
        return PaymentVerificationResult(
            is_paid=is_paid,
            status=payment.status,
            external_reference=payment.external_reference or f"MOCK-{payment.reference}",
            amount=float(payment.amount),
            raw_data=payment.raw_payload or {"mode": "mock"},
        )

    def handle_webhook(self, request: HttpRequest) -> Dict[str, Any]:
        """Décode la requête webhook simulée."""
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        reference = body.get("reference") or request.GET.get("reference", "")
        status = body.get("status", "SUCCESS")
        is_paid = status in ("SUCCESS", "PAID", "COMPLETED")

        return {
            "reference": reference,
            "is_paid": is_paid,
            "status": status,
            "external_reference": f"MOCK-WEBHOOK-{reference}",
            "raw_data": body,
        }
