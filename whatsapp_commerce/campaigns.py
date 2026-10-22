import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from whatsapp_agent.meta_templates import message_parameters
from whatsapp_agent.models import MessageEnvoi

from .inbox import normalize_phone
from .models import BusinessWhatsAppConnection, BusinessWhatsAppMessage
from .onboarding import MetaOnboardingError, _request_meta


def _connection_for_business(business):
    connection = BusinessWhatsAppConnection.objects.filter(
        business=business,
        status=BusinessWhatsAppConnection.Status.ACTIVE,
        phone_registered=True,
        webhook_subscribed=True,
    ).first()
    if connection is None:
        raise MetaOnboardingError("Le compte WhatsApp Business n’est pas entièrement connecté.")
    return connection


def _template_catalog(connection):
    cache_key = f"wa-business-campaign-templates:{connection.waba_id}"
    catalog = cache.get(cache_key)
    if catalog is not None:
        return catalog

    response = _request_meta(
        "GET",
        f"{connection.waba_id}/message_templates",
        token=connection.get_access_token(),
        params={"fields": "name,status,language,category,components", "limit": 100},
    )
    templates = response.get("data", [])
    if not isinstance(templates, list):
        raise MetaOnboardingError("Meta a retourné un catalogue de modèles invalide.")

    from .automations import _body_variable_count

    catalog = []
    for template in templates:
        if not isinstance(template, dict) or template.get("status") != "APPROVED":
            continue
        category = str(template.get("category", "")).upper()
        body = ""
        try:
            parameter_count = _body_variable_count(template)
            body = next(
                (
                    str(component.get("text", ""))
                    for component in template.get("components", [])
                    if isinstance(component, dict)
                    and str(component.get("type", "")).upper() == "BODY"
                ),
                "",
            )
            supported = category == "MARKETING"
            reason = "" if supported else "Les campagnes PME exigent un modèle de catégorie MARKETING."
        except MetaOnboardingError as exc:
            parameter_count = 0
            supported = False
            reason = str(exc)
        catalog.append(
            {
                "key": f'{template.get("name", "")}|{template.get("language", "")}',
                "name": str(template.get("name", "")),
                "language": str(template.get("language", "")),
                "category": category,
                "body": body,
                "parameter_count": parameter_count,
                "supported": supported,
                "reason": reason,
            }
        )
    cache.set(cache_key, catalog, 120)
    return catalog


def business_campaign_template_catalog(business):
    connection = _connection_for_business(business)
    if not connection.get_access_token():
        raise MetaOnboardingError("Le jeton WhatsApp Business est indisponible.")
    return _template_catalog(connection)


def validate_business_campaign_template(business, name, language, params):
    connection = _connection_for_business(business)
    if not connection.get_access_token():
        raise MetaOnboardingError("Le jeton WhatsApp Business est indisponible.")
    key = f"{name}|{language}"
    template = next((item for item in _template_catalog(connection) if item["key"] == key), None)
    if not template or not template["supported"]:
        reason = template["reason"] if template else "Ce modèle n’est pas approuvé pour le WABA de cette entreprise."
        raise MetaOnboardingError(reason)
    if len(params) != template["parameter_count"]:
        raise MetaOnboardingError(
            f"Ce modèle attend {template['parameter_count']} variable(s) de corps."
        )
    return connection, template


def send_business_campaign_message(message):
    contact = message.business_contact
    campaign = message.campagne
    if (
        contact is None
        or contact.business_id != campaign.business_id
        or contact.consent_marketing is not True
        or contact.marketing_opt_in is not True
        or contact.opted_out_at is not None
    ):
        return {
            "success": False,
            "message_id": "",
            "erreur": "Consentement marketing absent ou retiré avant l'envoi.",
        }

    connection = _connection_for_business(campaign.business)
    if getattr(settings, "WHATSAPP_DRY_RUN", True):
        return {
            "success": True,
            "message_id": f"dryrun-business-{message.pk}-{int(time.time() * 1000)}",
            "erreur": "Simulation : aucun appel Meta effectué.",
        }

    token = connection.get_access_token()
    if not token:
        return {"success": False, "message_id": "", "erreur": "Le jeton WhatsApp Business est indisponible."}

    if campaign.template_meta_name:
        _connection, template = validate_business_campaign_template(
            campaign.business,
            campaign.template_meta_name,
            campaign.template_meta_language,
            campaign.template_meta_params,
        )
        params = message_parameters(campaign, message)
        components = []
        if params:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": value} for value in params],
                }
            )
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalize_phone(contact.phone).lstrip("+"),
            "type": "template",
            "template": {
                "name": template["name"],
                "language": {"code": template["language"]},
                **({"components": components} if components else {}),
            },
        }
        message_type = "template"
        message_body = template["body"]
    else:
        if not contact.last_inbound_at or contact.last_inbound_at < timezone.now() - timedelta(hours=24):
            return {
                "success": False,
                "message_id": "",
                "erreur": "Hors de la fenêtre de 24 h : sélectionne un modèle MARKETING approuvé par Meta pour ce WABA.",
            }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalize_phone(contact.phone).lstrip("+"),
            "type": "text",
            "text": {"body": message.message_final, "preview_url": False},
        }
        message_type = "text"
        message_body = message.message_final

    response = _request_meta(
        "POST",
        f"{connection.phone_number_id}/messages",
        token=token,
        payload=payload,
    )
    wa_messages = response.get("messages", [])
    wa_message_id = str(wa_messages[0].get("id", "")) if wa_messages else ""
    if not wa_message_id:
        return {"success": False, "message_id": "", "erreur": "Meta n’a pas confirmé la prise en charge du message."}

    BusinessWhatsAppMessage.objects.create(
        contact=contact,
        wa_message_id=wa_message_id,
        direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
        message_type=message_type,
        body=message_body,
        status="sent",
        meta_timestamp=timezone.now(),
    )
    return {"success": True, "message_id": wa_message_id, "erreur": ""}
