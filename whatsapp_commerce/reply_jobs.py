"""Claim and process incoming reply jobs without repeating external actions."""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from immobilier_cameroun.agency import is_estate_agency

from .activation import automatic_answer, connection_blockers
from .follow_ups import booking_cases
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
        now = timezone.now()
        fields = {"status": status, "updated_at": now}
        if not job.activation_code and (job.booking_help or status == Status.REVIEW):
            from .offer_tracking import recent_offer_click

            source = recent_offer_click(job.connection, job.message)
            property_id = job.follow_up_property_id or (source.property_listing_id if source else None)
            if not property_id and not job.booking_help:
                selected = contact.selected_property
                if selected and selected.agence_id == contact.business_id:
                    property_id = selected.pk
            fields.update(
                booking_help=job.booking_help,
                follow_up_property_id=property_id,
                follow_up_item_id=job.follow_up_item_id or (source.catalog_item_id if source and not property_id else None),
                follow_up_order_id=job.follow_up_order_id,
                follow_up_service_id=job.follow_up_service_id,
                follow_up_appointment_id=job.follow_up_appointment_id,
            )
        changed = running.update(**fields)
        if changed and job.booking_help:
            booking_cases(contact.business).filter(
                message__contact=contact, message_id__lt=job.message_id,
                follow_up_property_id=fields["follow_up_property_id"], follow_up_item_id=fields["follow_up_item_id"],
                follow_up_service_id=job.follow_up_service_id, follow_up_appointment_id=job.follow_up_appointment_id,
            ).update(follow_up_closed_at=now)
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

    from .workflows import pending_reschedule, respond_to_workflow

    if job.automation_action == "invalid":
        return Status.SKIPPED
    scheduled, command = (job.automation_message, None)
    if not scheduled and message.message_type == "text" and not job.automation_action:
        scheduled, command = pending_reschedule(connection, contact, message.body)
    if scheduled:
        reply, review = respond_to_workflow(job, connection, contact, scheduled, job.automation_action or "move", command)
        reply = _booking_handoff_reply(job, reply)
        if reply:
            send_business_reply(contact, reply, expected_phone_number_id=job.phone_number_id, reply_job_id=job.pk)
        if review:
            return Status.REVIEW
        return Status.SENT if reply else Status.SKIPPED
    if job.automation_action:
        return Status.SKIPPED

    if message.message_type == "text" and connection.agent_enabled and getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False):
        from .order_operations import customer_order_reply
        from .quote_views import accept_quote
        from .watches import customer_watch_reply

        outcome = (accept_quote(contact, message.body) or customer_watch_reply(connection, contact, message.body)
                   or customer_order_reply(contact, message.body, job))
        if outcome:
            reply, review = outcome
            send_business_reply(contact, reply, expected_phone_number_id=job.phone_number_id, reply_job_id=job.pk, require_agent_enabled=True)
            return Status.REVIEW if review else Status.SENT

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
    from business.models import BusinessCatalogItem
    from .brain import classify_intent
    from .bookings import booking_reply, catalogue_booking_service
    from .entitlements import require_whatsapp_entitlement
    from .offer_tracking import CATALOGUE_INTRO, catalogue_offer_path, recent_offer_click
    from .orchestrator import can_offer_order, is_explicit_draft_confirmation
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
    offer_click = recent_offer_click(connection, job.message)
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
        from .order_operations import customer_order_reply

        outcome = customer_order_reply(contact, body, job)
        if outcome:
            reply, review = outcome
            send_business_reply(contact, reply, expected_phone_number_id=job.phone_number_id, reply_job_id=job.pk, require_agent_enabled=True)
            return Status.REVIEW if review else Status.SENT
    if is_estate_agency(contact.business):
        from .estate import estate_reply

        reply = estate_reply(
            activation, contact, body, typed=typed, offer_click=offer_click, reply_message_id=job.message_id,
        )
    else:
        intent = classify_intent(body)
        catalogue_enabled = activation.answer_catalog or activation.assist_sales or activation.booking_service_id
        if (catalogue_enabled and offer_click and offer_click.entry_message_id == job.message_id
                and offer_click.catalog_item_id and (body.startswith(CATALOGUE_INTRO) or intent == "qualification")):
            item = offer_click.catalog_item
            if not item.is_active or item.business_id != contact.business_id or not contact.business.is_published:
                reply = "Cette offre n’est plus disponible. L’équipe peut te proposer une autre option."
            else:
                link = settings.SITE_URL.rstrip("/") + catalogue_offer_path(contact.business, item.pk)
                reply = f"{item.title} — {item.price_label or 'Prix sur demande'}.\n{item.description[:400]}\n{link}"
                if item.item_type == BusinessCatalogItem.ItemType.SERVICE and catalogue_booking_service(activation, contact, item):
                    reply += "\nÉcris RDV pour voir les prochains créneaux."
                elif activation.assist_sales and can_offer_order(connection, item):
                    reply += "\nÉcris COMMANDER ou COMMANDER 2 x pour choisir la quantité."
        elif typed and activation.assist_sales and (
            intent == "commande" or is_explicit_draft_confirmation(contact, body)
        ):
            return _run_sales_agent(connection, contact, job.message, reply_job_id=job.pk, offer_click=offer_click)
        else:
            reply = booking_reply(
                activation, contact, body, typed=typed, offer_click=offer_click, reply_message_id=job.message_id,
            )
            if reply is None and intent in {"paiement", "rdv", "commande"}:
                return Status.REVIEW
    if reply is None:
        reply = automatic_answer(activation, body)
    reply = _booking_handoff_reply(job, reply)
    if not reply:
        return Status.REVIEW
    send_business_reply(
        contact, reply, expected_phone_number_id=job.phone_number_id, reply_job_id=job.pk,
        require_agent_enabled=True,
    )
    return Status.SENT


def _booking_handoff_reply(job, reply):
    from .bookings import BookingHandoff

    if isinstance(reply, BookingHandoff):
        job.booking_help = reply.reason
        job.follow_up_property_id = reply.listing_id
        job.follow_up_service_id = reply.service_id
        job.follow_up_appointment_id = reply.appointment_id
        return reply.reply
    return reply


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
