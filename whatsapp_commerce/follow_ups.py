"""Open WhatsApp cases backed by messages, bookings and existing payment records."""

from django.db.models import Exists, F, OuterRef, Q
from django.utils import timezone

from .checkout import verified_order_payment
from .models import BusinessWhatsAppReplyJob, WhatsAppDraftOrder


def payment_cases(business):
    return WhatsAppDraftOrder.objects.filter(
        business=business, contact__business=business, status=WhatsAppDraftOrder.Status.CONFIRMED,
        boutique_order__isnull=False, follow_up_closed_at__isnull=True,
    ).exclude(boutique_order__statut="annulee").exclude(
        Q(payment_transaction__commande_id=F("boutique_order__pk"))
        & (verified_order_payment() | Q(payment_transaction__statut="rembourse"))
    )


def open_jobs(business):
    return BusinessWhatsAppReplyJob.objects.filter(
        connection__business=business, message__contact__business=business,
        activation_code="", message__is_activation_test=False, follow_up_closed_at__isnull=True,
        message__contact__opted_out_at__isnull=True,
    )


def review_cases(business):
    reviews = open_jobs(business).filter(status=BusinessWhatsAppReplyJob.Status.REVIEW, booking_help="")
    later_review = BusinessWhatsAppReplyJob.objects.filter(
        message__contact_id=OuterRef("message__contact_id"), connection_id=OuterRef("connection_id"),
        activation_code="", booking_help="", status=BusinessWhatsAppReplyJob.Status.REVIEW,
        message_id__gt=OuterRef("message_id"),
    )
    return reviews.filter(~Exists(later_review))


def booking_cases(business):
    return open_jobs(business).exclude(booking_help="")


def close_booking_cases(contact, appointment, listing, *, reply_message_id):
    if reply_message_id is None:
        return
    subject = (
        Q(follow_up_property_id=listing.pk) if listing else
        Q(follow_up_property__isnull=True, follow_up_service_id=appointment.service_id, follow_up_service__isnull=False)
    )
    booking_cases(contact.business).filter(
        message__contact=contact, message_id__lt=reply_message_id,
    ).filter(
        Q(follow_up_appointment=appointment) | (Q(follow_up_appointment__isnull=True) & subject)
    ).update(follow_up_closed_at=timezone.now())
