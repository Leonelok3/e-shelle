"""Server-side Meta Embedded Signup onboarding for E-Shelle business profiles."""

import re

import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import BusinessWhatsAppConnection, ScheduledBusinessWhatsAppMessage


class MetaOnboardingError(RuntimeError):
    def __init__(self, message, code=""):
        super().__init__(message)
        self.code = str(code or "")


def _graph_url(path):
    version = getattr(settings, "WHATSAPP_GRAPH_API_VERSION", "v25.0")
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise MetaOnboardingError("La version de l’API Meta configurée est invalide.")
    return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"


def _request_meta(method, path, *, params=None, token="", payload=None, form_data=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if payload is not None and form_data is None:
        headers["Content-Type"] = "application/json"
    try:
        response = requests.request(
            method,
            _graph_url(path),
            params=params,
            json=payload if form_data is None else None,
            data=form_data,
            headers=headers,
            timeout=(5, 20),
        )
    except requests.RequestException as exc:
        raise MetaOnboardingError("Meta est temporairement indisponible. Réessayez.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise MetaOnboardingError("Meta a retourné une réponse illisible.") from exc

    if not response.ok or not isinstance(data, dict) or data.get("error"):
        error = data.get("error", {}) if isinstance(data, dict) else {}
        code = error.get("code", "")
        raise MetaOnboardingError(
            f"Meta a refusé une étape de connexion (code {code or 'inconnu'}).",
            code=code,
        )
    return data


def _exchange_signup_code(code):
    app_id = getattr(settings, "WHATSAPP_TECH_PROVIDER_APP_ID", "").strip()
    app_secret = getattr(settings, "WHATSAPP_TECH_PROVIDER_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise MetaOnboardingError("La connexion Meta n’est pas encore configurée par E-Shelle.")
    result = _request_meta(
        "GET",
        "oauth/access_token",
        params={"client_id": app_id, "client_secret": app_secret, "code": code},
    )
    token = result.get("access_token", "")
    if not isinstance(token, str) or not token:
        raise MetaOnboardingError("Meta n’a pas fourni de jeton d’accès.")
    return token


def _finish_connection(connection, pin):
    token = connection.get_access_token()
    if not token:
        connection.status = BusinessWhatsAppConnection.Status.ACTION_REQUIRED
        connection.last_error = "Le jeton est indisponible. Reconnectez le compte WhatsApp."
        connection.save(update_fields=["status", "last_error", "updated_at"])
        return False

    try:
        if not connection.phone_registered:
            _request_meta(
                "POST",
                f"{connection.phone_number_id}/register",
                token=token,
                payload={"messaging_product": "whatsapp", "pin": pin},
            )
            connection.phone_registered = True
            connection.save(update_fields=["phone_registered", "updated_at"])
        if not connection.webhook_subscribed:
            _request_meta(
                "POST",
                f"{connection.waba_id}/subscribed_apps",
                token=token,
                payload={},
            )
            connection.webhook_subscribed = True
            connection.save(update_fields=["webhook_subscribed", "updated_at"])
    except MetaOnboardingError as exc:
        connection.status = BusinessWhatsAppConnection.Status.ACTION_REQUIRED
        connection.last_error = str(exc)[:500]
        connection.save(update_fields=["status", "last_error", "updated_at"])
        return False

    connection.status = BusinessWhatsAppConnection.Status.ACTIVE
    connection.last_error = ""
    connection.connected_at = timezone.now()
    connection.save(update_fields=["status", "last_error", "connected_at", "updated_at"])
    return True


def connect_business(business, *, code, waba_id, phone_number_id, meta_business_id, pin):
    """Exchange the one-time Embedded Signup code and finish the Tech Provider setup."""
    if not re.fullmatch(r"\d{6}", pin or ""):
        raise MetaOnboardingError("Le code PIN WhatsApp doit contenir exactement 6 chiffres.")
    if not re.fullmatch(r"\d{1,64}", waba_id or ""):
        raise MetaOnboardingError("L’identifiant WABA retourné par Meta est invalide.")
    if not re.fullmatch(r"\d{1,64}", phone_number_id or ""):
        raise MetaOnboardingError("L’identifiant du numéro WhatsApp retourné par Meta est invalide.")
    if meta_business_id and not re.fullmatch(r"\d{1,64}", meta_business_id):
        raise MetaOnboardingError("L’identifiant Business retourné par Meta est invalide.")
    if not isinstance(code, str) or not code or len(code) > 4096:
        raise MetaOnboardingError("Le code temporaire retourné par Meta est invalide.")

    existing = BusinessWhatsAppConnection.objects.filter(business=business).first()
    if existing and existing.status != BusinessWhatsAppConnection.Status.DISCONNECTED:
        raise MetaOnboardingError("Déconnectez le compte WhatsApp existant avant d’en connecter un autre.")
    conflict = BusinessWhatsAppConnection.objects.exclude(business=business).filter(
        Q(waba_id=waba_id) | Q(phone_number_id=phone_number_id)
    ).exists()
    if conflict:
        raise MetaOnboardingError("Ce compte ou numéro WhatsApp est déjà relié à une autre fiche E-Shelle.")

    token = _exchange_signup_code(code)
    if existing:
        ScheduledBusinessWhatsAppMessage.objects.filter(
            connection=existing,
            status=ScheduledBusinessWhatsAppMessage.Status.SCHEDULED,
        ).update(
            status=ScheduledBusinessWhatsAppMessage.Status.CANCELLED,
            last_error="La connexion WhatsApp a été remplacée ; planifiez de nouveau après vérification.",
            updated_at=timezone.now(),
        )
        connection = existing
        connection.waba_id = waba_id
        connection.phone_number_id = phone_number_id
        connection.meta_business_id = meta_business_id
        connection.catalog_id = ""
        connection.display_phone_number = ""
        connection.phone_registered = False
        connection.webhook_subscribed = False
        connection.status = BusinessWhatsAppConnection.Status.CONNECTING
    else:
        connection = BusinessWhatsAppConnection(
            business=business,
            waba_id=waba_id,
            phone_number_id=phone_number_id,
            meta_business_id=meta_business_id,
        )
    connection.set_access_token(token)
    connection.save()
    return connection, _finish_connection(connection, pin)


def retry_connection_setup(connection, pin):
    if not re.fullmatch(r"\d{6}", pin or ""):
        raise MetaOnboardingError("Le code PIN WhatsApp doit contenir exactement 6 chiffres.")
    if connection.status != BusinessWhatsAppConnection.Status.ACTION_REQUIRED:
        raise MetaOnboardingError("Cette connexion ne nécessite pas de reprise.")
    return _finish_connection(connection, pin)
