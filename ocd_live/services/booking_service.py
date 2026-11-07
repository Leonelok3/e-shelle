import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..models import Booking, Slot, LiveSession, OCDPackage


def create_booking_for_session(user, session: LiveSession, whatsapp_number: str = "", package: OCDPackage = None):
    """Crée une réservation pour une session Live."""
    with transaction.atomic():
        amount = Decimal("0.00")
        if package:
            amount = package.price_xaf
        elif session.access_tier != LiveSession.AccessTier.FREE:
            amount = session.ticket_price_xaf

        status = Booking.Status.CONFIRMED if amount == 0 else Booking.Status.PENDING

        booking = Booking.objects.create(
            user=user,
            session=session,
            package=package,
            amount_paid=amount,
            status=status,
            whatsapp_number=whatsapp_number or getattr(user, "telephone", "") or getattr(user, "phone", ""),
        )
        return booking


def create_booking_for_slot(user, slot: Slot, whatsapp_number: str = ""):
    """Réserve un créneau privé avec un expert d'opportunité."""
    with transaction.atomic():
        locked_slot = Slot.objects.select_for_update().get(pk=slot.pk)
        if locked_slot.is_full or not locked_slot.is_active:
            raise ValueError("Ce créneau n'est plus disponible.")

        amount = locked_slot.price_xaf
        status = Booking.Status.CONFIRMED if amount == 0 else Booking.Status.PENDING

        booking = Booking.objects.create(
            user=user,
            slot=locked_slot,
            amount_paid=amount,
            status=status,
            whatsapp_number=whatsapp_number or getattr(user, "telephone", "") or "",
        )

        if status == Booking.Status.CONFIRMED:
            locked_slot.booked_count += 1
            locked_slot.save(update_fields=["booked_count"])

        return booking


def confirm_booking_payment(booking: Booking, transaction_ref: str = ""):
    """Valide définitivement une réservation après confirmation de paiement."""
    with transaction.atomic():
        booking.refresh_from_db()
        booking.status = Booking.Status.CONFIRMED
        booking.transaction_ref = transaction_ref
        booking.save(update_fields=["status", "transaction_ref", "updated_at"])

        if booking.slot:
            slot = Slot.objects.select_for_update().get(pk=booking.slot.pk)
            slot.booked_count += 1
            slot.save(update_fields=["booked_count"])

        # Envoi de la notification WhatsApp automatique
        try:
            from .whatsapp_alerts import send_booking_whatsapp_confirmation
            send_booking_whatsapp_confirmation(booking)
        except Exception:
            pass

        return booking

