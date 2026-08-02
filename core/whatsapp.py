"""Helpers for E-Shelle WhatsApp contact links."""
from urllib.parse import quote

from django.conf import settings


DEFAULT_SUPPORT_NUMBER = "237680625082"


def support_whatsapp_number() -> str:
    raw = (
        getattr(settings, "WHATSAPP_SUPPORT", "")
        or getattr(settings, "AUTO_WHATSAPP_CONTACT", "")
        or getattr(settings, "IMMO_WHATSAPP_CONTACT", "")
        or DEFAULT_SUPPORT_NUMBER
    )
    number = "".join(ch for ch in str(raw) if ch.isdigit())
    if number.startswith("237"):
        return number
    return f"237{number}" if number else DEFAULT_SUPPORT_NUMBER


def whatsapp_url(message: str, number: str | None = None) -> str:
    target = number or support_whatsapp_number()
    return f"https://wa.me/{target}?text={quote(message)}"


def user_contact_label(user) -> str:
    if not getattr(user, "is_authenticated", False):
        return "Client non connecte"
    name = user.get_full_name() or user.get_username()
    email = getattr(user, "email", "") or "email non renseigne"
    return f"{name} ({email})"


def payment_request_url(*, service: str, amount=None, user=None, details: str = "") -> str:
    amount_line = f"\nMontant affiche: {amount}" if amount not in (None, "", 0) else ""
    details_line = f"\nDetails: {details}" if details else ""
    message = (
        "Bonjour E-Shelle, je veux activer/payer un service premium."
        f"\nService: {service}"
        f"{amount_line}"
        f"\nClient: {user_contact_label(user)}"
        f"{details_line}"
        "\nMerci de me confirmer le bon plan et de m'envoyer mon code d'acces apres validation."
    )
    return whatsapp_url(message)
