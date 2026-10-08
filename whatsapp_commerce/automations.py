"""Consent-gated, single-contact WhatsApp template follow-ups."""

import logging
import json
import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .entitlements import require_whatsapp_entitlement
from .models import (
    BusinessWhatsAppContact,
    BusinessWhatsAppConnection,
    BusinessWhatsAppMessage,
    ScheduledBusinessWhatsAppMessage,
)
from .onboarding import MetaOnboardingError, _request_meta
from .services import normalize_phone

logger = logging.getLogger(__name__)
_BODY_VARIABLE = re.compile(r"\{\{\s*(\d+)\s*\}\}")


def _connection_for_business(business):
    connection = BusinessWhatsAppConnection.objects.filter(
        business=business,
        status=BusinessWhatsAppConnection.Status.ACTIVE,
    ).first()
    if connection is None or not connection.get_access_token():
        raise MetaOnboardingError("Connectez le compte WhatsApp Business de cette fiche.")
    return connection


def get_approved_template_catalog(business):
    if not require_whatsapp_entitlement(business, "can_automate"):
        raise MetaOnboardingError("Les relances automatiques nécessitent une formule Business active.")
    connection = _connection_for_business(business)
    result = _request_meta(
        "GET",
        f"{connection.waba_id}/message_templates",
        token=connection.get_access_token(),
        params={
            "fields": "name,status,language,category,components",
            "limit": 100,
        },
    )
    templates = result.get("data", [])
    if not isinstance(templates, list):
        raise MetaOnboardingError("Meta a retourné un catalogue de modèles invalide.")
    return [
        template for template in templates
        if isinstance(template, dict)
        and template.get("status") == "APPROVED"
        and str(template.get("category", "")).upper() in {"MARKETING", "UTILITY"}
    ]


def _body_variable_count(template):
    body = None
    components = template.get("components", [])
    if not isinstance(components, list):
        raise MetaOnboardingError("Meta a retourné des composants de modèle invalides.")
    for component in components:
        if not isinstance(component, dict):
            continue
        component_type = str(component.get("type", "")).upper()
        text = str(component.get("text", ""))
        if component_type == "HEADER" and str(component.get("format", "TEXT")).upper() != "TEXT":
            raise MetaOnboardingError("Les en-têtes média ou dynamiques de ce modèle ne sont pas pris en charge.")
        if component_type not in {"BODY", "HEADER", "FOOTER", "BUTTONS"}:
            raise MetaOnboardingError("Ce type de composant Meta n’est pas pris en charge.")
        if component_type == "BODY":
            body = text
            remaining = {key: value for key, value in component.items() if key != "text"}
            if _BODY_VARIABLE.search(json.dumps(remaining, ensure_ascii=False)):
                raise MetaOnboardingError(
                    "Ce modèle contient des variables de bouton non prises en charge."
                )
        elif _BODY_VARIABLE.search(json.dumps(component, ensure_ascii=False)):
            raise MetaOnboardingError(
                "Ce modèle contient des variables dans un en-tête ou un bouton non pris en charge."
            )
    if body is None:
        return 0
    numbers = [int(value) for value in _BODY_VARIABLE.findall(body)]
    expected = list(range(1, max(numbers, default=0) + 1))
    if sorted(set(numbers)) != expected:
        raise MetaOnboardingError("Les variables du corps du modèle ne sont pas séquentielles.")
    return len(expected)


def _find_approved_template(business, name, language):
    for template in get_approved_template_catalog(business):
        if template.get("name") == name and template.get("language") == language:
            _body_variable_count(template)
            return template
    raise MetaOnboardingError("Ce modèle et cette langue ne sont pas approuvés par Meta pour ce WABA.")


def schedule_template_follow_up(
    contact,
    *,
    template_name,
    template_language,
    body_parameters,
    scheduled_for,
    created_by,
):
    if not getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False):
        raise MetaOnboardingError("Les relances WhatsApp sont désactivées par la configuration de sécurité.")
    business = contact.business
    if not require_whatsapp_entitlement(business, "can_automate"):
        raise MetaOnboardingError("Les relances automatiques nécessitent une formule Business active.")
    if not contact.marketing_opt_in or not contact.consented_at or contact.opted_out_at:
        raise MetaOnboardingError("Un consentement marketing explicite et actif est obligatoire.")
    if not normalize_phone(contact.phone):
        raise MetaOnboardingError("Le numéro du contact n’est pas valide.")
    now = timezone.now()
    if scheduled_for < now + timedelta(minutes=2) or scheduled_for > now + timedelta(days=30):
        raise MetaOnboardingError("Choisissez une date entre 2 minutes et 30 jours à partir de maintenant.")
    if not re.fullmatch(r"[a-z0-9_]{1,128}", template_name or ""):
        raise MetaOnboardingError("Le nom du modèle Meta est invalide.")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{2,32}", template_language or ""):
        raise MetaOnboardingError("La langue du modèle Meta est invalide.")
    if not isinstance(body_parameters, list) or any(
        not isinstance(value, str) or not value.strip() or len(value) > 1024
        for value in body_parameters
    ):
        raise MetaOnboardingError("Les paramètres doivent être une liste de textes non vides.")

    template = _find_approved_template(business, template_name, template_language)
    if _body_variable_count(template) != len(body_parameters):
        raise MetaOnboardingError("Le nombre de valeurs ne correspond pas aux variables du corps du modèle.")
    connection = _connection_for_business(business)
    return ScheduledBusinessWhatsAppMessage.objects.create(
        contact=contact,
        connection=connection,
        template_name=template_name,
        template_language=template_language,
        body_parameters=[value.strip() for value in body_parameters],
        scheduled_for=scheduled_for,
        created_by=created_by,
    )


def cancel_scheduled_contact_messages(contact, reason="Le consentement de contact est inactif."):
    return ScheduledBusinessWhatsAppMessage.objects.filter(
        contact=contact,
        status=ScheduledBusinessWhatsAppMessage.Status.SCHEDULED,
    ).update(
        status=ScheduledBusinessWhatsAppMessage.Status.CANCELLED,
        last_error=reason[:500],
        updated_at=timezone.now(),
    )


def cancel_all_scheduled_follow_ups(reason):
    return ScheduledBusinessWhatsAppMessage.objects.filter(
        status=ScheduledBusinessWhatsAppMessage.Status.SCHEDULED,
    ).update(
        status=ScheduledBusinessWhatsAppMessage.Status.CANCELLED,
        last_error=reason[:500],
        updated_at=timezone.now(),
    )


def send_scheduled_template_message(message_id):
    if not getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False):
        ScheduledBusinessWhatsAppMessage.objects.filter(
            pk=message_id,
            status=ScheduledBusinessWhatsAppMessage.Status.SCHEDULED,
        ).update(
            status=ScheduledBusinessWhatsAppMessage.Status.CANCELLED,
            last_error="Les relances WhatsApp sont désactivées côté serveur.",
            updated_at=timezone.now(),
        )
        return False
    with transaction.atomic():
        scheduled = (
            ScheduledBusinessWhatsAppMessage.objects.select_for_update()
            .select_related("contact__business", "connection")
            .filter(pk=message_id)
            .first()
        )
        if (
            scheduled is None
            or scheduled.status != ScheduledBusinessWhatsAppMessage.Status.SCHEDULED
            or scheduled.scheduled_for > timezone.now()
        ):
            return False
        scheduled.status = ScheduledBusinessWhatsAppMessage.Status.SENDING
        scheduled.last_error = ""
        scheduled.save(update_fields=["status", "last_error", "updated_at"])

    contact = scheduled.contact
    try:
        business = contact.business
        if not require_whatsapp_entitlement(business, "can_automate"):
            raise MetaOnboardingError("La formule Business n’est plus active.")
        if not contact.marketing_opt_in or not contact.consented_at or contact.opted_out_at:
            raise MetaOnboardingError("Le consentement marketing n’est plus actif.")
        connection = BusinessWhatsAppConnection.objects.filter(
            pk=scheduled.connection_id,
            business=business,
            status=BusinessWhatsAppConnection.Status.ACTIVE,
        ).first()
        if connection is None or not connection.get_access_token():
            raise MetaOnboardingError("La connexion WhatsApp n’est plus active.")
        template = _find_approved_template(
            business,
            scheduled.template_name,
            scheduled.template_language,
        )
        if _body_variable_count(template) != len(scheduled.body_parameters):
            raise MetaOnboardingError("Les variables du modèle approuvé ont changé depuis la planification.")
        business.refresh_from_db()
        contact = BusinessWhatsAppContact.objects.get(pk=scheduled.contact_id)
        if not require_whatsapp_entitlement(business, "can_automate"):
            raise MetaOnboardingError("La formule Business n’est plus active.")
        if not contact.marketing_opt_in or not contact.consented_at or contact.opted_out_at:
            raise MetaOnboardingError("Le consentement marketing n’est plus actif.")
        if contact.business_id != connection.business_id or scheduled.connection_id != connection.pk:
            raise MetaOnboardingError("Le contact et le WABA planifié ne correspondent plus.")

        template_payload = {
            "name": scheduled.template_name,
            "language": {"code": scheduled.template_language},
        }
        if scheduled.body_parameters:
            template_payload["components"] = [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": value}
                    for value in scheduled.body_parameters
                ],
            }]
        response = _request_meta(
            "POST",
            f"{connection.phone_number_id}/messages",
            token=connection.get_access_token(),
            payload={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": normalize_phone(contact.phone).lstrip("+"),
                "type": "template",
                "template": template_payload,
            },
        )
        wa_messages = response.get("messages", [])
        wa_message_id = str(wa_messages[0].get("id", "")) if wa_messages else ""
        if not wa_message_id:
            raise MetaOnboardingError("Meta n’a pas confirmé la prise en charge du modèle.")
        BusinessWhatsAppMessage.objects.create(
            contact=contact,
            wa_message_id=wa_message_id,
            direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
            message_type="template",
            body=f"Modèle envoyé : {scheduled.template_name}",
            status="sent",
            meta_timestamp=timezone.now(),
        )
        scheduled.status = ScheduledBusinessWhatsAppMessage.Status.SENT
        scheduled.wa_message_id = wa_message_id
        scheduled.sent_at = timezone.now()
        scheduled.last_error = ""
        scheduled.save(update_fields=[
            "status", "wa_message_id", "sent_at", "last_error", "updated_at",
        ])
        return True
    except MetaOnboardingError as exc:
        scheduled.status = ScheduledBusinessWhatsAppMessage.Status.FAILED
        scheduled.last_error = str(exc)[:500]
    except Exception:
        scheduled.status = ScheduledBusinessWhatsAppMessage.Status.FAILED
        scheduled.last_error = "Échec de l’envoi. Vérifiez le statut Meta avant toute nouvelle planification."
        logger.exception("WhatsApp Business: relance planifiée en échec (message_id=%s).", message_id)
    scheduled.save(update_fields=["status", "last_error", "updated_at"])
    return False


def send_due_template_follow_ups(limit=10):
    if not getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False):
        cancel_all_scheduled_follow_ups("Les relances WhatsApp sont désactivées côté serveur.")
        return 0
    due_ids = list(
        ScheduledBusinessWhatsAppMessage.objects.filter(
            status=ScheduledBusinessWhatsAppMessage.Status.SCHEDULED,
            scheduled_for__lte=timezone.now(),
        ).order_by("scheduled_for", "pk").values_list("pk", flat=True)[:limit]
    )
    return sum(send_scheduled_template_message(message_id) for message_id in due_ids)
