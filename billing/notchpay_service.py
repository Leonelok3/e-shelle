"""
Service NotchPay — Immigration97
API doc: https://developer.notchpay.co
"""
import hashlib
import hmac
import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

NOTCHPAY_API_URL = "https://api.notchpay.co"


def _public_key() -> str:
    return getattr(settings, "NOTCHPAY_PUBLIC_KEY", "")


def _hash_key() -> str:
    return getattr(settings, "NOTCHPAY_HASH_KEY", "")


# ──────────────────────────────────────────────────────────────
# 1. INITIALISER UN PAIEMENT
# ──────────────────────────────────────────────────────────────

def initialize_payment(
    *,
    amount_xaf: int,
    email: str,
    reference: str,
    description: str,
    callback_url: str,
    name: str = "",
    phone: str = "",
) -> dict:
    """
    Crée une session de paiement NotchPay.
    Retourne {"success": True, "authorization_url": "...", "reference": "..."} ou {"success": False, "error": "..."}
    """
    if not _public_key():
        return {"success": False, "error": "NOTCHPAY_PUBLIC_KEY non configuré."}

    payload = {
        "amount": amount_xaf,
        "currency": "XAF",
        "email": email,
        "reference": reference,
        "description": description,
        "callback": callback_url,
    }
    if name:
        payload["name"] = name
    if phone:
        payload["phone"] = phone

    try:
        resp = requests.post(
            f"{NOTCHPAY_API_URL}/payments/initialize",
            json=payload,
            headers={
                "Authorization": _public_key(),
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        data = resp.json()
        logger.info("NotchPay initialize — status=%s ref=%s", resp.status_code, reference)

        # NotchPay retourne code 201 pour succès
        if resp.status_code in (200, 201) and data.get("status") in ("Accepted", "OK"):
            txn = data.get("transaction", {})
            return {
                "success": True,
                "authorization_url": txn.get("authorization_url", ""),
                "reference": txn.get("reference", reference),
            }

        return {
            "success": False,
            "error": data.get("message", f"Erreur HTTP {resp.status_code}"),
        }

    except requests.RequestException as exc:
        logger.exception("NotchPay initialize — réseau: %s", exc)
        return {"success": False, "error": "Erreur réseau, réessaie dans un instant."}


# ──────────────────────────────────────────────────────────────
# 2. VÉRIFIER UN PAIEMENT (après callback)
# ──────────────────────────────────────────────────────────────

def verify_payment(reference: str) -> dict:
    """
    Vérifie le statut d'un paiement via son reference NotchPay.
    Retourne {"success": True, "status": "complete"|"failed"|..., "amount": int}
    """
    if not _public_key():
        return {"success": False, "error": "NOTCHPAY_PUBLIC_KEY non configuré."}

    try:
        resp = requests.get(
            f"{NOTCHPAY_API_URL}/payments/{reference}",
            headers={
                "Authorization": _public_key(),
                "Accept": "application/json",
            },
            timeout=30,
        )
        data = resp.json()
        logger.info("NotchPay verify — status=%s ref=%s", resp.status_code, reference)

        if resp.status_code == 200:
            txn = data.get("transaction", {})
            status = txn.get("status", "").lower()
            return {
                "success": True,
                "status": status,  # "complete", "failed", "pending", "canceled"
                "amount": txn.get("amount", 0),
                "currency": txn.get("currency", "XAF"),
                "raw": txn,
            }

        return {
            "success": False,
            "error": data.get("message", f"Erreur HTTP {resp.status_code}"),
        }

    except requests.RequestException as exc:
        logger.exception("NotchPay verify — réseau: %s", exc)
        return {"success": False, "error": "Erreur réseau."}


# ──────────────────────────────────────────────────────────────
# 3. VÉRIFIER LA SIGNATURE WEBHOOK
# ──────────────────────────────────────────────────────────────

def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Vérifie la signature HMAC-SHA256 envoyée par NotchPay dans le header X-Notch-Signature.
    """
    hash_key = _hash_key()
    if not hash_key:
        logger.warning("NOTCHPAY_HASH_KEY non configuré — webhook non vérifié.")
        return True  # en dev sans clé, on laisse passer

    expected = hmac.new(
        hash_key.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header or "")


# ──────────────────────────────────────────────────────────────
# 4. GÉNÉRER UNE RÉFÉRENCE UNIQUE
# ──────────────────────────────────────────────────────────────

def make_reference(prefix: str = "IMM97") -> str:
    """Génère une référence unique ex: IMM97-a3f8c2d1"""
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
