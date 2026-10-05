from urllib.parse import urlsplit

import requests
from django.conf import settings


class WhatsAppCallingError(Exception):
    pass


def _graph_request(path, method="GET", params=None, payload=None):
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        raise WhatsAppCallingError("Configuration WhatsApp Meta absente.")
    configured = urlsplit(settings.WHATSAPP_API_URL)
    if configured.scheme != "https" or configured.hostname != "graph.facebook.com":
        raise WhatsAppCallingError("L’API Meta doit utiliser graph.facebook.com en HTTPS.")
    version = configured.path.strip("/").split("/")[0]
    url = f"https://graph.facebook.com/{version}/{path.lstrip('/')}"
    try:
        response = requests.request(
            method,
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            params=params,
            json=payload,
            timeout=(5, 20),
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WhatsAppCallingError(f"Meta est indisponible ({type(exc).__name__}).") from None
    if response.status_code >= 400 or data.get("error"):
        error = data.get("error", {})
        code = error.get("code", "?")
        message = str(error.get("message", "Erreur Meta"))[:300]
        raise WhatsAppCallingError(f"Meta {response.status_code}, code {code}: {message}")
    return data


def get_call_permission(phone_number):
    return _graph_request(
        f"{settings.WHATSAPP_PHONE_ID}/call_permissions",
        params={"user_wa_id": phone_number.lstrip("+")},
    )


def request_call_permission(phone_number, context="E-Shelle souhaite vous appeler sur WhatsApp pour répondre à votre demande."):
    return _graph_request(
        f"{settings.WHATSAPP_PHONE_ID}/messages",
        method="POST",
        payload={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number.lstrip("+"),
            "type": "interactive",
            "interactive": {
                "type": "call_permission_request",
                "action": {"name": "call_permission_request"},
                "body": {"text": context[:1024]},
            },
        },
    )


def post_call_action(call_id, action, session=None):
    payload = {
        "messaging_product": "whatsapp",
        "call_id": call_id,
        "action": action,
    }
    if session:
        payload["session"] = session
    return _graph_request(
        f"{settings.WHATSAPP_PHONE_ID}/calls",
        method="POST",
        payload=payload,
    )


def initiate_call(phone_number, sdp_offer, callback_data):
    return _graph_request(
        f"{settings.WHATSAPP_PHONE_ID}/calls",
        method="POST",
        payload={
            "messaging_product": "whatsapp",
            "to": phone_number.lstrip("+"),
            "action": "connect",
            "session": {"sdp_type": "offer", "sdp": sdp_offer},
            "biz_opaque_callback_data": callback_data,
        },
    )
