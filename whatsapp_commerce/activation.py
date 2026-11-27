"""Guided setup and a controlled WhatsApp test for an individual business."""

import re
import unicodedata

from django.conf import settings
from django.utils import timezone

from .models import BusinessWhatsAppActivation, BusinessWhatsAppConnection, BusinessWhatsAppReplyJob
from .services import normalize_phone


TEST_SUFFIX = re.compile(r"\s+\[ESHELLE-TEST:([0-9a-f]{16})\]\s*$", re.I)
DELIVERED = {"delivered", "read"}
SEND_CONFIRMED = DELIVERED | {"accepted", "sent"}


def connection_blockers(connection):
    if connection is None:
        return ["Connecte le compte WhatsApp Business de cette entreprise."]
    missing = []
    if not connection.phone_registered:
        missing.append("L’enregistrement du numéro auprès de Meta est incomplet.")
    if not connection.webhook_subscribed:
        missing.append("L’abonnement aux notifications de messages Meta est incomplet.")
    if not connection.get_access_token():
        missing.append("L’autorisation Meta doit être renouvelée.")
    if not getattr(settings, "WHATSAPP_APP_SECRET", ""):
        missing.append("La signature des notifications Meta doit être configurée côté E-Shelle.")
    if connection.status != BusinessWhatsAppConnection.Status.ACTIVE:
        missing.append("Reprends la connexion WhatsApp dans la section de connexion.")
    return missing


def selected_catalog(connection):
    return connection.agent_catalog_items.filter(
        business_id=connection.business_id, is_active=True,
    ).order_by("order", "pk")


def configuration_blockers(activation):
    if activation is None:
        return ["Enregistre les réglages de l’agent."]
    if not (activation.answer_hours or activation.answer_catalog):
        return ["Choisis au moins un sujet à tester."]
    missing = []
    if activation.answer_hours and not activation.opening_hours:
        missing.append("Renseigne les horaires d’ouverture.")
    if activation.answer_catalog and not selected_catalog(activation.connection).exists():
        missing.append("Choisis au moins un article actif du catalogue.")
    return missing


def test_question(activation):
    return "Quels sont vos horaires ?" if activation.answer_hours else "Puis-je voir votre catalogue ?"


def test_body(activation):
    return f"{test_question(activation)} [ESHELLE-TEST:{activation.test_code}]"


def automatic_answer(activation, body):
    """Reply with the configured facts for a supported question."""
    normalized = unicodedata.normalize("NFKD", body.casefold())
    normalized = "".join(letter for letter in normalized if not unicodedata.combining(letter))
    if activation.answer_hours and activation.opening_hours and re.search(
        r"\b(horaires?|ouvert(?:e|s|es)?|ouverture|fermez|heures? d'ouverture|opening hours|open)\b",
        normalized,
    ):
        return f"Voici nos horaires d’ouverture :\n{activation.opening_hours}"
    if activation.answer_catalog and re.search(r"\b(menu|carte|catalogue?|catalog|tarifs?)\b", normalized):
        items = list(selected_catalog(activation.connection)[:8])
        if items:
            lines = [f"• {item.title} — {item.price_label or 'prix sur demande'}" for item in items]
            return "Voici une sélection de notre catalogue :\n" + "\n".join(lines)
    return ""


def activation_context(connection):
    activation = (
        BusinessWhatsAppActivation.objects.select_related("test_message__reply_job", "test_reply")
        .filter(connection=connection).first() if connection else None
    )
    job = getattr(activation.test_message, "reply_job", None) if activation else None
    reply = activation.test_reply if activation else None
    current_test = bool(activation and activation.test_phone_number_id == connection.phone_number_id)
    open_test = bool(
        current_test and activation.test_expires_at and activation.test_expires_at > timezone.now()
        and activation.test_message_id is None
    )
    blockers = connection_blockers(connection)
    setup_blockers = configuration_blockers(activation)
    enabled = getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False)
    outbound_status = reply.status if current_test and reply else ""
    ready = enabled and not blockers and not setup_blockers
    running = current_test and job and (
        job.status == BusinessWhatsAppReplyJob.Status.PROCESSING
        or (job.status == BusinessWhatsAppReplyJob.Status.PENDING and activation.test_expires_at > timezone.now())
    )
    return {
        "setup": activation,
        "connection_blockers": blockers,
        "setup_blockers": setup_blockers,
        "test_ready": ready,
        "test_pending": bool(open_test),
        "test_body": test_body(activation) if open_test else "",
        "test_destination": normalize_phone(connection.display_phone_number).lstrip("+") if open_test else "",
        "test_job": job if current_test else None,
        "test_status": outbound_status,
        "test_received": outbound_status in DELIVERED,
        "test_can_confirm": outbound_status in SEND_CONFIRMED - DELIVERED,
        "test_running": bool(running),
        "can_enable": ready and not connection.agent_enabled and outbound_status in SEND_CONFIRMED,
    }
