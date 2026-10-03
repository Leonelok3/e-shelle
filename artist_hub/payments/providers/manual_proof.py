"""
artist_hub/payments/providers/manual_proof.py
Fournisseur pour les paiements directs MoMo, Orange Money et Virement Ecobank
avec téléversement obligatoire du justificatif de paiement et validation par l'administrateur.
"""
from typing import Optional, Dict, Any
from django.urls import reverse
from django.http import HttpRequest
from .base import BasePaymentProvider, PaymentResult, PaymentVerificationResult
from artist_hub.payments.models import PaymentStatus
from artist_hub.conf import hub_settings


class ManualProofProvider(BasePaymentProvider):
    """
    Gestion des paiements directs vers les comptes officiels OPLUS :
    - Orange Money : +237 695 487 796
    - MTN MoMo : +237 675 293 836
    - Ecobank RIB : 4020789949967166
    Avec preuve de paiement téléversée et validation staff.
    """

    name: str = "manual_proof"

    def initiate(self, payment, return_url: Optional[str] = None) -> PaymentResult:
        """
        Oriente le candidat vers la page d'instructions de paiement et de dépôt de preuve.
        """
        waiting_url = reverse("artist_hub:payments:waiting", kwargs={"reference": payment.reference})
        return PaymentResult(
            success=True,
            payment_url=waiting_url,
            reference=payment.reference,
            message="Instructions de virement MoMo / OM / Ecobank affichées",
            raw_data={
                "provider": "manual_proof",
                "orange_money": hub_settings.ORANGE_MONEY_NUMBER,
                "mtn_momo": hub_settings.MTN_MOMO_NUMBER,
                "ecobank_rib": hub_settings.ECOBANK_RIB,
            },
        )

    def verify(self, reference: str) -> PaymentVerificationResult:
        """
        Vérifie si l'administrateur a validé la transaction.
        """
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
            external_reference=payment.external_reference or "",
            amount=float(payment.amount),
            raw_data=payment.raw_payload or {},
        )

    def handle_webhook(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Le mode manuel ne reçoit pas de webhook direct des opérateurs télécoms,
        mais accepte une requête de validation interne si authentifiée.
        """
        reference = request.POST.get("reference") or request.GET.get("reference", "")
        return {
            "reference": reference,
            "is_paid": False,
            "status": "MANUAL_PENDING",
            "raw_data": {"mode": "manual_proof"},
        }
