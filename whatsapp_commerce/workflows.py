"""Object-scoped operational messages sharing the scheduled WhatsApp queue."""

import re
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from immobilier_cameroun.models import StatutVisite
from salonhub.bookings.models import Appointment

from .checkout import checkout_enabled, checkout_url, verified_order_payment
from .entitlements import require_whatsapp_entitlement
from .models import BusinessWhatsAppBooking, BusinessWhatsAppConnection, BusinessWhatsAppWorkflow, ScheduledBusinessWhatsAppMessage, WhatsAppDraftOrder, WhatsAppWatch
from .onboarding import MetaOnboardingError

Kind = BusinessWhatsAppWorkflow.Kind
Status = ScheduledBusinessWhatsAppMessage.Status
BUTTONS = {
    Kind.BOOKING: (("confirm", "Confirmer ma présence"), ("reschedule", "Reporter")),
    Kind.PAYMENT: (),
    Kind.AFTER_BOOKING: (("feedback", "Répondre"),),
    Kind.AFTER_ORDER: (("feedback", "Répondre"),),
    Kind.WAITLIST: (),
    Kind.PROPERTY: (),
    Kind.SHIPPING: (),
}
PARAMETERS = {
    Kind.BOOKING: "Prestation ou bien, puis date et heure",
    Kind.PAYMENT: "Référence de commande, puis lien CamPay",
    Kind.AFTER_BOOKING: "Prestation ou bien, puis nom de l’entreprise",
    Kind.AFTER_ORDER: "Référence de commande, puis nom de l’entreprise",
    Kind.WAITLIST: "Prestation ou bien, puis créneau disponible et commande WhatsApp",
    Kind.PROPERTY: "Titre du bien compatible, puis lien vers le bien",
    Kind.SHIPPING: "Référence de commande, puis information de livraison",
}
ACTION = re.compile(r"esflow:([0-9a-f]{32}):(confirm|reschedule|feedback)")
POLL_WINDOW = timedelta(hours=2)


class ObsoleteWorkflow(MetaOnboardingError):
    """Business data made a planned send unnecessary."""


def validate_workflow_template(kind, template):
    from .automations import _body_variable_count

    categories = {"UTILITY", "MARKETING"} if kind == Kind.PROPERTY else {"UTILITY"}
    if template.get("category", "").upper() not in categories or _body_variable_count(template) != 2:
        raise MetaOnboardingError("Choisis un modèle approuvé dans la catégorie indiquée, avec deux variables dans le texte.")
    buttons = [button for part in template.get("components", []) if part.get("type", "").upper() == "BUTTONS"
               for button in part.get("buttons", [])]
    actual = [(entry.get("type", "").upper(), entry.get("text", "").strip()) for entry in buttons]
    expected = [("QUICK_REPLY", label) for _, label in BUTTONS[kind]]
    if actual != expected:
        raise MetaOnboardingError("Les boutons du modèle doivent correspondre aux boutons indiqués, dans le même ordre.")


def appointment_at(booking):
    return timezone.make_aware(datetime.combine(booking.appointment.date, booking.appointment.time))


def booking_subject(booking):
    if booking.property_visit_id:
        return booking.property_visit.bien.titre
    return booking.appointment.service.name if booking.appointment.service_id else "Rendez-vous"


def _bookings(business):
    return BusinessWhatsAppBooking.objects.filter(
        contact__business=business, appointment__salon__owner_id=business.owner_id,
    ).filter(
        Q(property_visit__isnull=True) | Q(property_visit__bien__agence=business, property_visit__statut=StatutVisite.CONFIRME),
    ).select_related("appointment__service", "property_visit__bien", "contact")


def _orders(business):
    return WhatsAppDraftOrder.objects.filter(
        business=business, contact__business=business, connection__business=business,
        status=WhatsAppDraftOrder.Status.CONFIRMED, boutique_order__business_profile=business,
        boutique_order__whatsapp_contact_id=F("contact_id"),
    ).select_related("boutique_order", "payment_transaction", "contact")


def _booking_key(booking, kind):
    if kind == Kind.AFTER_BOOKING:
        return f"{kind}:{booking.pk}"
    return f"{kind}:{booking.pk}:{booking.schedule_revision}:{booking.appointment.date}:{booking.appointment.time}"


def _remembered_booking_matches(message, booking):
    return message.workflow_key == _booking_key(booking, Kind.BOOKING)


def _eligible_contact(rows):
    return rows.filter(contact__consent_service=True, contact__opted_out_at__isnull=True, contact__agent_paused=False).filter(
        Q(contact__consent_marketing=True) | Q(contact__marketing_opt_in=True, contact__consented_at__isnull=False),
    )


def _payment_orders(business):
    return _orders(business).filter(
        boutique_order__statut="en_attente", payment_transaction__methode="campay",
        payment_transaction__statut__in=["initie", "en_attente", "pending_awaiting_manual_validation"],
        payment_transaction__commande_id=F("boutique_order__pk"),
    ).exclude(verified_order_payment()).filter(
        Q(payment_transaction__metadata__campay__provider_status__isnull=True)
        | ~Q(payment_transaction__metadata__campay__provider_status="SUCCESSFUL"),
    )


def _shipped_orders(business):
    from .order_operations import paid_orders

    return paid_orders(_orders(business)).filter(fulfillment_stage="shipped", boutique_order__statut__in=["en_attente", "payee"])


def _upcoming(rule, now, delay):
    if rule.kind == Kind.BOOKING:
        start, end = now, now + delay
        rows = _bookings(rule.business).filter(appointment__status=Appointment.Status.CONFIRMED, presence_confirmed_at__isnull=True)
        rows = rows.filter(appointment__date__range=(timezone.localdate(start), timezone.localdate(end)))
        for booking in _eligible_contact(rows).iterator():
            event = appointment_at(booking)
            if now < event <= end:
                yield booking, None, max(event - delay, now), _booking_key(booking, rule.kind)
    elif rule.kind == Kind.AFTER_BOOKING:
        anchor = now - delay
        rows = _bookings(rule.business).filter(
            appointment__status=Appointment.Status.DONE, completed_at__gte=anchor - POLL_WINDOW, completed_at__lte=anchor,
        )
        for booking in _eligible_contact(rows).iterator():
            yield booking, None, booking.completed_at + delay, _booking_key(booking, rule.kind)
    else:
        anchor = now - delay
        if rule.kind == Kind.PAYMENT:
            if not checkout_enabled(rule.business_id):
                return
            rows = _payment_orders(rule.business).filter(confirmed_at__range=(anchor - POLL_WINDOW, anchor))
        elif rule.kind == Kind.SHIPPING:
            rows = _shipped_orders(rule.business).filter(boutique_order__updated_at__range=(anchor - POLL_WINDOW, anchor))
        else:
            rows = _orders(rule.business).filter(boutique_order__statut="livree", boutique_order__updated_at__range=(anchor - POLL_WINDOW, anchor))
        for order in _eligible_contact(rows).iterator():
            started = order.confirmed_at if rule.kind == Kind.PAYMENT else order.boutique_order.updated_at
            yield None, order, started + delay, f"{rule.kind}:{order.pk}"


def plan_workflows(now=None):
    from .watches import match_watch, watch_key

    now = now or timezone.now()
    ScheduledBusinessWhatsAppMessage.objects.filter(
        workflow__isnull=False, status=Status.SENDING, updated_at__lt=now - timedelta(minutes=10),
    ).update(
        status=Status.FAILED, updated_at=now,
        last_error="Accusé de réception manquant. Vérifie la livraison dans Meta.",
    )
    rules = BusinessWhatsAppWorkflow.objects.filter(
        enabled=True, business__whatsapp_connection__status=BusinessWhatsAppConnection.Status.ACTIVE,
        business__whatsapp_connection__automations_enabled=True,
    ).select_related("business__whatsapp_connection")
    for rule in rules.iterator():
        connection = rule.business.whatsapp_connection
        if not require_whatsapp_entitlement(rule.business, "can_automate"):
            continue
        delay = timedelta(hours=rule.delay_hours)
        if rule.kind in WhatsAppWatch.Kind.values:
            rows = _eligible_contact(WhatsAppWatch.objects.filter(
                active=True, kind=rule.kind, contact__business=rule.business, requested_at__lte=now - delay,
            ).select_related("service__salon", "listing", "contact__business"))
            for watch in rows.iterator():
                match = match_watch(watch)
                if match:
                    _enqueue(rule, connection, watch.contact, now, watch_key(watch), workflow_watch=watch, workflow_match=match[0])
            continue
        for booking, order, due, key in _upcoming(rule, now, delay):
            if due < rule.updated_at and rule.kind != Kind.BOOKING:
                continue
            _enqueue(rule, connection, (booking or order).contact, due, key, workflow_booking=booking, workflow_order=order)


def _enqueue(rule, connection, contact, due, key, **source):
    values = {**source, "workflow": rule, "contact": contact, "connection": connection,
              "workflow_phone": connection.phone_number_id, "workflow_revision": rule.updated_at,
              "template_name": rule.template_name, "template_language": rule.template_language, "scheduled_for": due}
    queued, created = ScheduledBusinessWhatsAppMessage.objects.get_or_create(workflow_key=key, defaults=values)
    if (not created and queued.status == Status.CANCELLED and not queued.sent_at
            and (queued.workflow_revision != rule.updated_at or queued.workflow_match != source.get("workflow_match", ""))):
        ScheduledBusinessWhatsAppMessage.objects.filter(pk=queued.pk, status=Status.CANCELLED).update(
            **values, status=Status.SCHEDULED, last_error="", updated_at=timezone.now(),
        )


def workflow_parameters(message, contact, connection):
    """Re-read the actual business state immediately before the external send."""
    rule = BusinessWhatsAppWorkflow.objects.filter(pk=message.workflow_id, business_id=contact.business_id, enabled=True).first()
    if (rule is None or not connection.automations_enabled or message.workflow_phone != connection.phone_number_id
            or message.workflow_revision != rule.updated_at
            or rule.template_name != message.template_name or rule.template_language != message.template_language
            or connection.status != BusinessWhatsAppConnection.Status.ACTIVE or contact.agent_paused or not contact.consent_service):
        raise ObsoleteWorkflow("Automatisation, consentement ou numéro modifié depuis la planification.")
    now = timezone.now()
    delay = timedelta(hours=rule.delay_hours)
    if message.workflow_watch_id:
        from .watches import match_watch, watch_key

        watch = WhatsAppWatch.objects.select_related("service__salon", "listing", "contact__business").filter(
            pk=message.workflow_watch_id, active=True, kind=rule.kind, contact=contact, requested_at__lte=now - delay,
        ).first()
        if watch and watch_key(watch) == message.workflow_key:
            match = match_watch(watch)
            if match and match[0] == message.workflow_match:
                return match[1]
        raise ObsoleteWorkflow("L’alerte ou l’offre disponible a changé depuis la planification.")
    if message.workflow_booking_id:
        booking = _bookings(contact.business).filter(pk=message.workflow_booking_id, contact=contact).first()
        if booking and rule.kind == Kind.BOOKING:
            event = appointment_at(booking)
            if (booking.appointment.status == Appointment.Status.CONFIRMED and not booking.presence_confirmed_at
                    and _remembered_booking_matches(message, booking) and event - delay <= now < event):
                local = timezone.localtime(event)
                return [booking_subject(booking), f"{local:%d/%m/%Y à %H:%M} ({timezone.get_current_timezone_name()})"]
        if (booking and rule.kind == Kind.AFTER_BOOKING and booking.appointment.status == Appointment.Status.DONE
                and booking.completed_at and booking.completed_at + delay <= now
                and message.scheduled_for >= now - POLL_WINDOW):
            return [booking_subject(booking), contact.business.name]
    if message.workflow_order_id and message.scheduled_for >= now - POLL_WINDOW:
        if rule.kind == Kind.SHIPPING:
            order = _shipped_orders(contact.business).filter(pk=message.workflow_order_id, contact=contact, connection=connection).first()
            if order and order.boutique_order.updated_at + delay <= now:
                return [order.boutique_order.reference, order.delivery_note or "Ta commande est en cours de livraison."]
        if rule.kind == Kind.PAYMENT and checkout_enabled(contact.business_id):
            order = _payment_orders(contact.business).filter(pk=message.workflow_order_id, contact=contact, connection=connection).first()
            if order and order.confirmed_at and order.confirmed_at + delay <= now:
                if order.payment_transaction.ref_operateur:
                    from payments.campay import CampayError, reconcile_transaction

                    try:
                        reconcile_transaction(order.payment_transaction)
                    except CampayError as exc:
                        raise MetaOnboardingError("CamPay est indisponible pour vérifier le paiement en attente.") from exc
                if _payment_orders(contact.business).filter(pk=order.pk, contact=contact, connection=connection).exists():
                    return [order.boutique_order.reference, checkout_url(order.payment_transaction)]
        if rule.kind == Kind.AFTER_ORDER:
            order = _orders(contact.business).filter(pk=message.workflow_order_id, contact=contact, connection=connection, boutique_order__statut="livree").first()
            if order and order.boutique_order.updated_at + delay <= now:
                return [order.boutique_order.reference, contact.business.name]
    raise ObsoleteWorkflow("Le rendez-vous ou la commande a changé depuis la planification.")


def workflow_buttons(message):
    return [{"type": "button", "sub_type": "quick_reply", "index": str(index), "parameters": [
        {"type": "payload", "payload": f"esflow:{message.workflow_token.hex}:{action}"},
    ]} for index, (action, _) in enumerate(BUTTONS[message.workflow.kind])]


def _mapping(value):
    return value if isinstance(value, dict) else {}


def extract_workflow_action(connection, contact, payload):
    button = _mapping(payload.get("button"))
    interactive = _mapping(payload.get("interactive"))
    callback = str(button.get("payload") or _mapping(interactive.get("button_reply")).get("id") or "")
    parsed = ACTION.fullmatch(callback)
    context_id = _mapping(payload.get("context")).get("id")
    if not parsed and not context_id:
        return None, "invalid" if callback.startswith("esflow:") else ""
    rows = ScheduledBusinessWhatsAppMessage.objects.filter(
        connection=connection, contact=contact, workflow_phone=connection.phone_number_id,
        status=Status.SENT, sent_at__gte=timezone.now() - timedelta(days=7), workflow__isnull=False,
    )
    if context_id:
        rows = rows.filter(wa_message_id=context_id)
    if parsed:
        message = rows.filter(workflow_token=parsed[1]).select_related("workflow").first()
        if message and parsed[2] in {action for action, _ in BUTTONS[message.workflow.kind]}:
            return message, parsed[2]
    elif payload.get("type", "text") in {"text", "audio"}:
        message = rows.filter(workflow__kind__in=[Kind.AFTER_BOOKING, Kind.AFTER_ORDER]).first()
        if message:
            return message, "feedback"
    return None, "invalid" if callback.startswith("esflow:") else ""


def pending_reschedule(connection, contact, body):
    from .bookings import COMMAND

    command = COMMAND.fullmatch(body.strip())
    if not command or not command["ref"]:
        return None, command
    message = ScheduledBusinessWhatsAppMessage.objects.filter(
        connection=connection, contact=contact, workflow_phone=connection.phone_number_id,
        workflow__kind=Kind.BOOKING, status=Status.SENT, workflow_action="reschedule",
        workflow_booking__appointment_id=command["ref"], sent_at__gte=timezone.now() - timedelta(days=7),
    ).order_by("-sent_at").first()
    return message, command


@transaction.atomic
def respond_to_workflow(job, connection, contact, scheduled, action, command=None):
    from datetime import date, time

    from .bookings import _book, _suggest_slots

    scheduled = ScheduledBusinessWhatsAppMessage.objects.select_for_update().filter(
        pk=scheduled.pk, status=Status.SENT, connection=connection, contact=contact,
        workflow_phone=connection.phone_number_id,
    ).first()
    if not scheduled:
        return "", False
    booking = _bookings(contact.business).filter(pk=scheduled.workflow_booking_id, contact=contact).first()
    if booking and booking.property_visit_id:
        job.follow_up_property_id = booking.property_visit.bien_id
    if scheduled.workflow_order_id:
        job.follow_up_item_id = _orders(contact.business).filter(
            pk=scheduled.workflow_order_id, contact=contact,
        ).values_list("catalog_item_id", flat=True).first()
    if action == "feedback":
        if scheduled.workflow_action == "feedback" and job.message.message_type == "button":
            return "", False
        _record_action(scheduled, "feedback")
        text = "Écris ta réponse ici. L’équipe pourra la lire et te répondre." if job.message.message_type in {"button", "interactive"} else ""
        return text, True
    if (not booking or booking.appointment.status != Appointment.Status.CONFIRMED
            or appointment_at(booking) <= timezone.now() or not _remembered_booking_matches(scheduled, booking)):
        if scheduled.workflow_action == "reschedule":
            _record_action(scheduled, "obsolete")
        return "Ce rappel n’est plus à jour. Vérifie le dernier créneau confirmé dans la conversation.", False
    if action == "confirm":
        if booking.presence_confirmed_at:
            return "", False
        booking.presence_confirmed_at = timezone.now()
        booking.save(update_fields=["presence_confirmed_at"])
        _record_action(scheduled, "confirmed")
        return "Ta présence est confirmée. À bientôt !", False
    listing = booking.property_visit.bien if booking.property_visit_id else None
    service = booking.appointment.service
    if service is None or not service.is_active or not booking.appointment.salon.is_active:
        return "L’équipe doit vérifier les créneaux de ce rendez-vous.", True
    if action == "reschedule":
        _record_action(scheduled, "reschedule")
        return _suggest_slots(service, listing, booking.appointment), False
    try:
        day = date.fromisoformat(command["date"])
        slot = time.fromisoformat(command["time"])
    except ValueError:
        return "Date ou heure invalide. Choisis l’un des créneaux proposés.", False
    reply = _book(
        service, contact, day, slot, booking.appointment_id, listing=listing, estate=bool(listing),
        reply_message_id=job.message_id,
    )
    booking.refresh_from_db()
    if not _remembered_booking_matches(scheduled, booking):
        _record_action(scheduled, "rescheduled")
    return reply, not bool(reply)


def _record_action(message, action):
    message.workflow_action = action
    message.workflow_responded_at = timezone.now()
    message.save(update_fields=["workflow_action", "workflow_responded_at", "updated_at"])
