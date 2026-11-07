import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction as db_transaction
from django.urls import reverse
from payments.models import Transaction
from ..models import Booking

logger = logging.getLogger(__name__)


def initiate_booking_payment(request, booking: Booking):
    """
    Crée une Transaction centrale E-Shelle et lance le paiement CamPay Mobile Money.
    Réutilise le service officiel de payments sans aucune duplication.
    """
    if booking.amount_paid <= 0:
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])
        return None

    from payments.views import _start_campay_checkout

    desc = f"OCD Live Ticket {booking.ticket_code}"
    if booking.session:
        desc = f"OCD Live: {booking.session.title[:40]}"
    elif booking.package:
        desc = f"OCD Pass: {booking.package.name}"
    elif booking.slot:
        desc = f"OCD Créneau: {booking.slot.title[:40]}"

    fallback_url = reverse("ocd_live:booking_detail", kwargs={"ticket_code": booking.ticket_code})

    with db_transaction.atomic():
        tx = Transaction.objects.create(
            utilisateur=request.user,
            type_tx="achat_produit",
            methode="campay",
            montant=booking.amount_paid,
            devise="XAF",
            telephone=booking.whatsapp_number,
            statut="initie",
            metadata={
                "product_type": "ocd_live_booking",
                "ocd_booking_id": booking.pk,
                "ticket_code": booking.ticket_code,
                "description": desc,
            },
        )
        booking.transaction_ref = tx.reference
        booking.save(update_fields=["transaction_ref"])

    return _start_campay_checkout(
        request,
        tx,
        description=desc,
        fallback_url=fallback_url,
    )

