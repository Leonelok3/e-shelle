"""
artist_hub/payments/providers/notchpay.py
Connecteur Notch Pay pour le Cameroun (MTN Mobile Money, Orange Money, Cartes Bancaires).
Prend en charge l'initiation de checkout, la vérification côté serveur et la validation de signature webhook HMAC-SHA256.
"""
import hmac
import hashlib
import json
import logging
from typing import Optional, Dict, Any
import requests
from django.http import HttpRequest
from .base import BasePaymentProvider, PaymentResult, PaymentVerificationResult
from artist_hub.conf import hub_settings

logger = logging.getLogger("artist_hub.payments.notchpay")


class NotchPayProvider(BasePaymentProvider):
    """Fournisseur d'agrégation Notch Pay pour paiements MoMo + OM + Carte."""

    name: str = "notchpay"

    def __init__(self):
        self.public_key = hub_settings.NOTCHPAY_PUBLIC_KEY
        self.private_key = hub_settings.NOTCHPAY_PRIVATE_KEY
        self.hash_key = hub_settings.NOTCHPAY_HASH_KEY
        self.base_url = hub_settings.NOTCHPAY_BASE_URL.rstrip("/")

    def initiate(self, payment, return_url: Optional[str] = None) -> PaymentResult:
        """
        Initie un paiement Notch Pay en créant une session de checkout hébergée.
        """
        url = f"{self.base_url}/checkout/initialize"
        headers = {
            "Authorization": self.public_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "amount": int(payment.amount),
            "currency": payment.currency or "XAF",
            "reference": payment.reference,
            "description": f"Paiement {hub_settings.BRAND_NAME} - {payment.reference}",
            "customer": {
                "name": payment.payer_name or "Candidat OPLUS",
                "email": payment.payer_email or f"{payment.reference}@oplusevent.com",
                "phone": payment.payer_phone or "",
            },
        }
        if return_url:
            payload["callback"] = return_url

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            data = response.json()
            if response.status_code in (200, 201) and data.get("authorization_url"):
                return PaymentResult(
                    success=True,
                    payment_url=data.get("authorization_url"),
                    reference=payment.reference,
                    message="Session Notch Pay initialisée avec succès",
                    raw_data=data,
                )
            else:
                error_msg = data.get("message") or f"Erreur Notch Pay ({response.status_code})"
                logger.error("Échec initialisation Notch Pay pour %s : %s", payment.reference, error_msg)
                return PaymentResult(
                    success=False,
                    reference=payment.reference,
                    message=error_msg,
                    raw_data=data,
                )
        except Exception as exc:
            logger.exception("Exception réseau Notch Pay lors de l'initiation de %s", payment.reference)
            return PaymentResult(
                success=False,
                reference=payment.reference,
                message=f"Erreur de communication avec la passerelle : {str(exc)}",
            )

    def verify(self, reference: str) -> PaymentVerificationResult:
        """
        Interroge l'API Notch Pay pour vérifier le paiement côté serveur.
        Ne dépend JAMAIS du navigateur client.
        """
        url = f"{self.base_url}/payments/{reference}"
        headers = {
            "Authorization": self.private_key or self.public_key,
            "Accept": "application/json",
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            data = response.json()
            if response.status_code == 200:
                tx = data.get("transaction") or data
                status = (tx.get("status") or "").lower()
                is_paid = status in ("complete", "completed", "success", "successful", "paid")
                return PaymentVerificationResult(
                    is_paid=is_paid,
                    status=status.upper(),
                    external_reference=str(tx.get("reference") or ""),
                    amount=float(tx.get("amount") or 0),
                    raw_data=data,
                )
            else:
                return PaymentVerificationResult(
                    is_paid=False,
                    status="FAILED",
                    error_message=data.get("message", "Transaction introuvable"),
                    raw_data=data,
                )
        except Exception as exc:
            logger.exception("Erreur lors de la vérification Notch Pay pour %s", reference)
            return PaymentVerificationResult(
                is_paid=False,
                status="ERROR",
                error_message=str(exc),
            )

    def verify_signature(self, request: HttpRequest) -> bool:
        """
        Vérifie la signature HMAC-SHA256 envoyée dans les en-têtes du webhook.
        """
        if not self.hash_key:
            logger.warning("NOTCHPAY_HASH_KEY non configurée : vérification de signature ignorée.")
            return True

        signature = (
            request.headers.get("X-Notch-Signature")
            or request.META.get("HTTP_X_NOTCH_SIGNATURE", "")
        )
        if not signature:
            logger.warning("Webhook Notch Pay sans en-tête X-Notch-Signature")
            return False

        try:
            computed = hmac.new(
                self.hash_key.encode("utf-8"),
                request.body,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(computed, signature)
        except Exception as exc:
            logger.exception("Erreur lors de la vérification de signature Notch Pay : %s", exc)
            return False

    def handle_webhook(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Valide la signature et extrait les informations de la transaction.
        """
        if not self.verify_signature(request):
            return {
                "reference": "",
                "is_paid": False,
                "status": "INVALID_SIGNATURE",
                "error": "Signature de webhook invalide",
                "raw_data": {},
            }

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = {}

        event = payload.get("event", "")
        data = payload.get("data") or {}
        reference = data.get("reference") or ""
        status = (data.get("status") or "").lower()
        is_paid = event == "payment.complete" or status in ("complete", "success", "paid")

        return {
            "reference": reference,
            "is_paid": is_paid,
            "status": status.upper() if status else ("SUCCESS" if is_paid else "PENDING"),
            "external_reference": str(data.get("id") or ""),
            "raw_data": payload,
        }
