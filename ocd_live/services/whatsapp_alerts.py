import logging
from django.conf import settings
from ..models import Booking

logger = logging.getLogger(__name__)


def send_booking_whatsapp_confirmation(booking: Booking):
    """
    Envoie une notification WhatsApp avec le billet et le lien d'accès.
    Utilise l'intégration officielle E-Shelle WhatsApp Cloud API si configurée,
    sinon journalise l'alerte.
    """
    if not booking.whatsapp_number:
        return False

    clean_phone = "".join(c for c in booking.whatsapp_number if c.isdigit() or c == "+")
    if not clean_phone.startswith("+"):
        if clean_phone.startswith("237"):
            clean_phone = "+" + clean_phone
        elif len(clean_phone) == 9:
            clean_phone = "+237" + clean_phone

    title = "Session Live"
    if booking.session:
        title = booking.session.title
    elif booking.package:
        title = booking.package.name
    elif booking.slot:
        title = booking.slot.title

    message = (
        f"🎙️ *OCD LIVE — Réservez, Présentez & Vendez en Direct*\n\n"
        f"Félicitations {booking.user.get_full_name() or booking.user.username} !\n"
        f"Votre accès est confirmé pour : *{title}*\n\n"
        f"🎟️ *Votre Code Billet :* `{booking.ticket_code}`\n"
        f"🔗 *Accéder à votre espace :* https://e-shelle.com/ocd-live/mon-espace/\n\n"
        f"Préparez-vous à présenter vos offres devant l'audience E-Shelle !"
    )

    logger.info("Envoi WhatsApp OCD Live vers %s pour ticket %s", clean_phone, booking.ticket_code)

    try:
        from whatsapp_agent.services import envoyer_message
        envoyer_message(clean_phone, message)
        booking.whatsapp_reminder_sent = True
        booking.save(update_fields=["whatsapp_reminder_sent"])
        return True
    except Exception as exc:
        logger.warning("Échec envoi notification WhatsApp OCD Live: %s", exc)
        return False

