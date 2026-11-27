"""Claim and process incoming reply jobs without repeating external actions."""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from immobilier_cameroun.agency import is_estate_agency

from .activation import automatic_answer, connection_blockers
from .inbox import AutomatedReplySuppressed, _refund_ai_credit, _reserve_ai_credit, _run_sales_agent, send_business_reply
from .models import (
    BusinessWhatsAppActivation,
    BusinessWhatsAppAudit,
    BusinessWhatsAppConnection,
    BusinessWhatsAppContact,
    BusinessWhatsAppMessage,
    BusinessWhatsAppReplyJob,
)

logger = logging.getLogger(__name__)
Status = BusinessWhatsAppReplyJob.Status
PROCESSING_TIMEOUT = timedelta(minutes=5)
DISPATCH_INTERVAL = timedelta(seconds=30)
BATCH_SIZE = 50


def _pause_contact(contact_id):
    BusinessWhatsAppContact.objects.filter(pk=contact_id).update(agent_paused=True)
    BusinessWhatsAppReplyJob.objects.filter(message__contact_id=contact_id, status=Status.PENDING).update(
        status=Status.SKIPPED, updated_at=timezone.now(),
    )


@transaction.atomic
def set_agent_paused(contact_id, paused):
    contact = BusinessWhatsAppContact.objects.select_for_update().get(pk=contact_id)
    if paused:
        _pause_contact(contact.pk)
    else:
        BusinessWhatsAppContact.objects.filter(pk=contact.pk).update(agent_paused=False)


def _claim(job_id):
    """Only the first available job for a contact may start."""
    job = BusinessWhatsAppReplyJob.objects.select_related("message").filter(pk=job_id).first()
    if job is None or job.status != Status.PENDING:
        return None
    contact_id = job.message.contact_id
    with transaction.atomic():
        contact = BusinessWhatsAppContact.objects.select_for_update().filter(pk=contact_id).first()
        if contact is None:
            return None
        blocked = BusinessWhatsAppReplyJob.objects.filter(message__contact_id=contact_id).exclude(pk=job_id).filter(
            Q(status=Status.PROCESSING) | Q(status=Status.PENDING, message_id__lt=job.message_id),
        ).exists()
        if blocked:
            return None
        if not BusinessWhatsAppReplyJob.objects.filter(pk=job_id, status=Status.PENDING).update(
            status=Status.PROCESSING, updated_at=timezone.now(),
        ):
            return None
    return job


def _finish(job, status, *, stalled_before=None):
    with transaction.atomic():
        contact = BusinessWhatsAppContact.objects.select_for_update().filter(pk=job.message.contact_id).first()
        if contact is None:
            return 0
        running = BusinessWhatsAppReplyJob.objects.filter(pk=job.pk, status=Status.PROCESSING)
        if stalled_before is not None:
            running = running.filter(updated_at__lt=stalled_before)
        changed = running.update(status=status, updated_at=timezone.now())
        if changed and status == Status.REVIEW and not job.activation_code:
            _pause_contact(contact.pk)
        return changed


def _respond(job):
    from .campaigns import accept_njangi_invitation

    message = job.message
    contact = BusinessWhatsAppContact.objects.select_related("business").filter(pk=message.contact_id).first()
    if contact is None or contact.opted_out_at or contact.agent_paused:
        return Status.SKIPPED
    if (message.meta_timestamp or message.created_at) < timezone.now() - timedelta(hours=24):
        return Status.SKIPPED
    connection = BusinessWhatsAppConnection.objects.filter(
        pk=job.connection_id, business_id=contact.business_id, phone_number_id=job.phone_number_id,
        status=BusinessWhatsAppConnection.Status.ACTIVE,
    ).first()
    if connection is None:
        return Status.REVIEW

    if job.activation_code:
        return _respond_to_test(job, connection, contact)

    if is_estate_agency(contact.business):
        activation = BusinessWhatsAppActivation.objects.filter(connection=connection).first()
        return _respond_with_scope(job, activation, connection, contact) if activation else Status.SKIPPED

    accepted = accept_njangi_invitation(contact, message.body)
    if not accepted:
        activation = BusinessWhatsAppActivation.objects.filter(connection=connection).first()
        if activation:
            return _respond_with_scope(job, activation, connection, contact)
        return _run_sales_agent(connection, contact, message, reply_job_id=job.pk)

    reply = (
        f"Participation confirmée : {accepted['quantity']} unité(s) à "
        f"{accepted['group'].prix_njangi}F. Merci pour ta réponse !"
    )
    wa_message_id = send_business_reply(
        contact, reply, expected_phone_number_id=job.phone_number_id, reply_job_id=job.pk,
    )
    BusinessWhatsAppAudit.objects.create(
        connection=connection,
        contact=contact,
        event_type="njangi_group_buy_accepted",
        action="explicit_oui",
        details={
            "group_buy_id": accepted["group"].pk,
            "quantity": accepted["quantity"],
            "wa_message_id": wa_message_id,
        },
    )
    return Status.SENT


def _respond_to_test(job, connection, contact):
    activation = BusinessWhatsAppActivation.objects.filter(
        connection=connection, test_message=job.message, test_code=job.activation_code,
        test_phone_number_id=job.phone_number_id, test_expires_at__gt=timezone.now(),
    ).first()
    if (
        activation is None
        or not getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False)
        or connection_blockers(connection)
    ):
        return Status.SKIPPED
    if is_estate_agency(connection.business):
        from .estate import estate_preview

        reply = estate_preview(connection.business)
    else:
        reply = automatic_answer(activation, job.message.body)
    if not reply:
        return Status.REVIEW
    outbound_id = send_business_reply(
        contact, reply, expected_phone_number_id=job.phone_number_id,
        reply_job_id=job.pk, activation_test=True,
    )
    outbound = BusinessWhatsAppMessage.objects.get(
        contact=contact, wa_message_id=outbound_id, is_activation_test=True,
    )
    BusinessWhatsAppActivation.objects.filter(pk=activation.pk, test_code=job.activation_code).update(
        test_reply=outbound,
    )
    return Status.SENT


def _respond_with_scope(job, activation, connection, contact):
    from .brain import classify_intent
    from .bookings import booking_reply
    from .entitlements import require_whatsapp_entitlement
    from .orchestrator import is_explicit_draft_confirmation
    from .voice import transcribe_voice, voice_available

    if (
        not connection.agent_enabled
        or not getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False)
        or not require_whatsapp_entitlement(contact.business, "can_use_crm")
        or (activation.activated_at and job.message.created_at < activation.activated_at)
    ):
        return Status.SKIPPED
    body = job.message.body
    typed = job.message.message_type in {"text", "interactive", "button"}
    if job.message.message_type == "audio":
        if (
            not activation.voice_enabled or not voice_available() or not job.message.media_id
            or not _reserve_ai_credit(contact.business)
        ):
            return Status.REVIEW
        try:
            body = transcribe_voice(connection, job.message)
        except Exception as exc:
            logger.warning("WhatsApp : transcription indisponible (job_id=%s, type=%s).", job.pk, type(exc).__name__)
            body = ""
        if not body:
            _refund_ai_credit(contact.business)
            return Status.REVIEW
        BusinessWhatsAppMessage.objects.filter(pk=job.message_id).update(body=body)
    if is_estate_agency(contact.business):
        from .estate import estate_reply

        reply = estate_reply(activation, contact, body, typed=typed)
    else:
        intent = classify_intent(body)
        if typed and activation.assist_sales and (
            intent == "commande" or is_explicit_draft_confirmation(contact, body)
        ):
            return _run_sales_agent(connection, contact, job.message, reply_job_id=job.pk)
        reply = booking_reply(activation, contact, body, typed=typed)
        if reply is None and intent in {"paiement", "rdv", "commande"}:
            return Status.REVIEW
    if reply is None:
        reply = automatic_answer(activation, body)
    if not reply:
        return Status.REVIEW
    send_business_reply(
        contact, reply, expected_phone_number_id=job.phone_number_id, reply_job_id=job.pk,
        require_agent_enabled=True,
    )
    return Status.SENT


def process_reply_job(job_id):
    job = _claim(job_id)
    if job is None:
        return False
    try:
        status = _respond(job)
    except AutomatedReplySuppressed:
        status = Status.SKIPPED
    except Exception:
        logger.exception("WhatsApp Commerce: réponse à vérifier (job_id=%s).", job.pk)
        status = Status.REVIEW
    _finish(job, status)
    return True


def dispatch_pending_jobs(publish):
    """Recover unscheduled work and leave interrupted sends to a human."""
    now = timezone.now()
    stalled_before = now - PROCESSING_TIMEOUT
    stalled = BusinessWhatsAppReplyJob.objects.select_related("message").filter(
        status=Status.PROCESSING, updated_at__lt=stalled_before,
    ).order_by("updated_at", "pk")[:BATCH_SIZE]
    for job in stalled:
        _finish(job, Status.REVIEW, stalled_before=stalled_before)

    blocking = BusinessWhatsAppReplyJob.objects.filter(message__contact_id=OuterRef("message__contact_id")).filter(
        Q(status=Status.PROCESSING) | Q(status=Status.PENDING, message_id__lt=OuterRef("message_id")),
    )
    pending = BusinessWhatsAppReplyJob.objects.filter(
        status=Status.PENDING, dispatch_after__lte=now,
    ).filter(~Exists(blocking)).order_by("dispatch_after", "pk").values_list("pk", flat=True)[:BATCH_SIZE]
    count = 0
    for job_id in list(pending):
        if not BusinessWhatsAppReplyJob.objects.filter(
            pk=job_id, status=Status.PENDING, dispatch_after__lte=now,
        ).update(dispatch_after=now + DISPATCH_INTERVAL):
            continue
        try:
            publish(job_id)
        except Exception:
            # The DB job remains due after the dispatch interval, including on an ambiguous broker failure.
            logger.warning("WhatsApp Commerce: publication Celery à reprendre (job_id=%s).", job_id, exc_info=True)
        else:
            count += 1
    return count
