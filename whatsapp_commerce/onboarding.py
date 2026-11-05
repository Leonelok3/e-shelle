"""Server-side Meta Embedded Signup onboarding for E-Shelle business profiles."""

import re

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import BusinessWhatsAppConnection, ScheduledBusinessWhatsAppMessage


EXISTING_WABA_TARGET_PUBLIC_SLUG = "immigration-canada-douala"


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


def get_assigned_applications(access_token):
    """Return the Meta applications assigned to the authenticated Tech Provider."""
    if not isinstance(access_token, str) or not access_token.strip():
        raise MetaOnboardingError("Un jeton utilisateur Meta est requis.")
    result = _request_meta(
        "GET",
        "me/assigned_applications",
        token=access_token,
        params={"fields": "id,name"},
    )
    applications = result.get("data", [])
    if not isinstance(applications, list):
        raise MetaOnboardingError("Meta a retourné une liste d’applications invalide.")
    return applications


def refresh_connection_metadata(connection):
    """Fetch the connected phone number's current status from Meta."""
    token = connection.get_access_token()
    if not token:
        raise MetaOnboardingError("Le jeton Meta de cette entreprise est indisponible.")
    result = _request_meta(
        "GET",
        connection.phone_number_id,
        token=token,
        params={
            "fields": (
                "id,display_phone_number,verified_name,status,quality_rating,"
                "whatsapp_business_manager_messaging_limit"
            )
        },
    )
    return result


def sync_existing_waba(business):
    """Attach the preconfigured, already-registered WABA to its designated profile."""
    if business.public_slug != EXISTING_WABA_TARGET_PUBLIC_SLUG:
        raise MetaOnboardingError("La synchronisation du WABA existant n’est pas autorisée pour cette fiche.")

    waba_id = str(getattr(settings, "WHATSAPP_WABA_ID", "")).strip()
    phone_number_id = str(
        getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        or getattr(settings, "WHATSAPP_PHONE_ID", "")
    ).strip()
    token = str(
        getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        or getattr(settings, "WHATSAPP_TOKEN", "")
    ).strip()
    meta_business_id = str(getattr(settings, "WHATSAPP_BUSINESS_ID", "")).strip()
    if not waba_id or not phone_number_id or not token:
        raise MetaOnboardingError("La configuration du compte WhatsApp existant est incomplète.")
    if not re.fullmatch(r"\d{1,64}", waba_id):
        raise MetaOnboardingError("L’identifiant WABA configuré est invalide.")
    if not re.fullmatch(r"\d{1,64}", phone_number_id):
        raise MetaOnboardingError("L’identifiant du numéro WhatsApp configuré est invalide.")
    if meta_business_id and not re.fullmatch(r"\d{1,64}", meta_business_id):
        raise MetaOnboardingError("L’identifiant Business configuré est invalide.")

    existing = BusinessWhatsAppConnection.objects.filter(business=business).first()
    if existing and (existing.waba_id != waba_id or existing.phone_number_id != phone_number_id):
        raise MetaOnboardingError(
            "Un autre compte WhatsApp est déjà associé à cette fiche. Il n’a pas été modifié."
        )
    conflict = BusinessWhatsAppConnection.objects.exclude(business=business).filter(
        Q(waba_id=waba_id) | Q(phone_number_id=phone_number_id)
    ).exists()
    if conflict:
        raise MetaOnboardingError("Ce compte ou numéro WhatsApp est déjà relié à une autre fiche E-Shelle.")

    phone_data = _request_meta(
        "GET",
        phone_number_id,
        token=token,
        params={
            "fields": (
                "id,display_phone_number,verified_name,status,quality_rating,"
                "whatsapp_business_manager_messaging_limit"
            )
        },
    )
    if str(phone_data.get("id", "")) != phone_number_id:
        raise MetaOnboardingError("Meta n’a pas confirmé l’identifiant du numéro configuré.")
    if phone_data.get("status") != "CONNECTED":
        raise MetaOnboardingError(
            "Meta indique que ce numéro n’est pas connecté à WhatsApp Cloud API."
        )

    waba_phones = _request_meta(
        "GET",
        f"{waba_id}/phone_numbers",
        token=token,
        params={"fields": "id", "limit": 1000},
    ).get("data")
    if not isinstance(waba_phones, list) or not any(
        isinstance(item, dict) and str(item.get("id", "")) == phone_number_id
        for item in waba_phones
    ):
        raise MetaOnboardingError("Meta n’a pas confirmé que ce numéro appartient au WABA configuré.")

    with transaction.atomic():
        existing = BusinessWhatsAppConnection.objects.select_for_update().filter(
            business=business,
        ).first()
        if existing and (existing.waba_id != waba_id or existing.phone_number_id != phone_number_id):
            raise MetaOnboardingError(
                "Un autre compte WhatsApp est déjà associé à cette fiche. Il n’a pas été modifié."
            )
        conflict = BusinessWhatsAppConnection.objects.exclude(business=business).filter(
            Q(waba_id=waba_id) | Q(phone_number_id=phone_number_id)
        ).exists()
        if conflict:
            raise MetaOnboardingError(
                "Ce compte ou numéro WhatsApp est déjà relié à une autre fiche E-Shelle."
            )

        connection = existing or BusinessWhatsAppConnection(business=business)
        connection.waba_id = waba_id
        connection.phone_number_id = phone_number_id
        if meta_business_id:
            connection.meta_business_id = meta_business_id
        connection.set_access_token(token)
        connection.display_phone_number = str(phone_data.get("display_phone_number", ""))[:32]
        connection.meta_verified_name = str(phone_data.get("verified_name", ""))[:180]
        connection.meta_phone_status = str(phone_data.get("status", ""))[:32]
        connection.meta_quality_rating = str(phone_data.get("quality_rating", ""))[:32]
        connection.meta_messaging_limit = str(
            phone_data.get("whatsapp_business_manager_messaging_limit", "")
        )[:64]
        connection.phone_registered = True
        connection.webhook_subscribed = False
        connection.status = BusinessWhatsAppConnection.Status.CONNECTING
        connection.last_error = ""
        connection.last_meta_sync_at = timezone.now()
        connection.save()

    try:
        resubscribe_connection_webhook(connection)
    except MetaOnboardingError as exc:
        connection.status = BusinessWhatsAppConnection.Status.ACTION_REQUIRED
        connection.last_error = str(exc)[:500]
        connection.save(update_fields=["status", "last_error", "updated_at"])
        raise

    connection.status = BusinessWhatsAppConnection.Status.ACTIVE
    connection.webhook_subscribed = True
    connection.last_error = ""
    connection.connected_at = connection.connected_at or timezone.now()
    connection.save(update_fields=[
        "status",
        "webhook_subscribed",
        "last_error",
        "connected_at",
        "updated_at",
    ])
    return connection


def deregister_connection_phone(connection):
    """Disable the connected phone number on Cloud API while retaining its local record."""
    token = connection.get_access_token()
    if not token:
        raise MetaOnboardingError("Le jeton Meta de cette entreprise est indisponible.")
    _request_meta("POST", f"{connection.phone_number_id}/deregister", token=token, payload={})


def resubscribe_connection_webhook(connection):
    """Restore the app subscription to the customer's WABA webhooks."""
    token = connection.get_access_token()
    if not token:
        raise MetaOnboardingError("Le jeton Meta de cette entreprise est indisponible.")
    _request_meta("POST", f"{connection.waba_id}/subscribed_apps", token=token, payload={})


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
