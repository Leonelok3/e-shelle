"""Capability links and verified payment status for WhatsApp orders."""

from urllib.parse import urlsplit

from django.conf import settings
from django.core import signing
from django.urls import reverse

CHECKOUT_SALT = "whatsapp-commerce.campay-checkout"
CHECKOUT_MAX_AGE = 7 * 24 * 60 * 60


def checkout_enabled(business_id):
    allowed = str(getattr(settings, "WHATSAPP_CAMPAY_BUSINESS_IDS", "")).split(",")
    base = urlsplit(getattr(settings, "CAMPAY_PUBLIC_BASE_URL", ""))
    return str(business_id) in {value.strip() for value in allowed} and base.scheme == "https" and bool(base.hostname)


def checkout_url(payment):
    token = signing.dumps({"id": payment.pk, "reference": payment.reference}, salt=CHECKOUT_SALT)
    path = reverse("payments:whatsapp_campay_order", kwargs={"token": token})
    return getattr(settings, "CAMPAY_PUBLIC_BASE_URL", "").rstrip("/") + path


def payment_status(payment):
    if payment is None:
        return "Commande confirmée"
    if payment.statut == "rembourse":
        return "Paiement remboursé"
    if payment.methode == "campay":
        verification = (payment.metadata or {}).get("campay") or {}
        if verification.get("provider_status") == "SUCCESSFUL" and verification.get("verified_at"):
            return "Paiement de test vérifié" if verification.get("mode") == "sandbox" else "Paiement vérifié"
    elif payment.statut == "succes":
        return "Paiement validé manuellement"
    if payment.statut in {"echec", "expire"}:
        return "Paiement à reprendre avec l’équipe"
    return "Paiement en attente"
