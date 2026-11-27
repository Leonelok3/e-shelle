"""Customer-requested availability and property notifications."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from immobilier_cameroun.agency import is_estate_agency, public_agency_properties
from salonhub.bookings.utils import get_available_slots

from .models import BusinessWhatsAppActivation, BusinessWhatsAppWorkflow, WhatsAppWatch

Kind = WhatsAppWatch.Kind
CRITERIA = {"type_transaction", "type_bien__in", "ville__iexact", "quartier__iexact", "prix__lte", "devise", "nombre_chambres__gte", "periode_prix"}


def customer_watch_reply(connection, contact, body):
    text = body.strip().casefold().replace("’", "'").replace("ê", "e")
    if text == "stop alertes":
        WhatsAppWatch.objects.filter(contact=contact, active=True).update(active=False)
        return "Tes alertes de disponibilité E‑Shelle ont été arrêtées.", False
    if text not in {"liste d'attente", "alerte biens"}:
        return None
    if not contact.consent_marketing and not (contact.marketing_opt_in and contact.consented_at):
        return "L’équipe doit enregistrer ton autorisation WhatsApp avant que je puisse activer cette alerte.", False
    kind = Kind.PROPERTY if text == "alerte biens" else Kind.WAITLIST
    if not (getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False) and connection.automations_enabled
            and BusinessWhatsAppWorkflow.objects.filter(business=contact.business, kind=kind, enabled=True).exists()):
        return "L’équipe peut t’aider à mettre en place cette alerte.", True
    if text == "alerte biens":
        if not is_estate_agency(contact.business):
            return "Cette commande est disponible auprès d’une agence immobilière.", False
        criteria = contact.property_filters if isinstance(contact.property_filters, dict) else {}
        criteria = {key: value for key, value in criteria.items() if key in CRITERIA}
        if not criteria:
            return "Indique d’abord la ville, le type de bien ou ton budget, puis écris ALERTE BIENS.", False
        _subscribe(contact, Kind.PROPERTY, criteria=criteria, service=None, listing=None)
        return "Je te signalerai le prochain bien de cette agence qui correspond à ta recherche. Écris STOP ALERTES pour arrêter.", False
    activation = BusinessWhatsAppActivation.objects.select_related("booking_service__salon").filter(connection=connection).first()
    if not activation or not activation.booking_service_id:
        return "L’équipe doit vérifier si un agenda est disponible.", True
    service = activation.booking_service
    if not service.is_active or not service.salon.is_active or service.salon.owner_id != contact.business.owner_id:
        return "L’équipe doit vérifier si un agenda est disponible.", True
    listing = None
    if is_estate_agency(contact.business):
        listing = public_agency_properties(contact.business).filter(pk=contact.selected_property_id).first()
        if not listing:
            return "Choisis d’abord un bien, puis écris LISTE D’ATTENTE.", False
    _subscribe(contact, Kind.WAITLIST, service=service, listing=listing, criteria={})
    return "Je te signalerai le prochain créneau disponible. La réservation se fera après ton choix. Écris STOP ALERTES pour arrêter.", False


def _subscribe(contact, kind, **values):
    WhatsAppWatch.objects.update_or_create(contact=contact, kind=kind, defaults={**values, "active": True, "requested_at": timezone.now()})


def match_watch(watch):
    business = watch.contact.business
    if watch.kind == Kind.PROPERTY:
        listing = public_agency_properties(business).filter(date_publication__gt=watch.requested_at, **watch.criteria).order_by("date_publication", "pk").first()
        if listing:
            return str(listing.pk), [listing.titre, settings.SITE_URL.rstrip("/") + listing.get_absolute_url()]
        return None
    service = watch.service
    if not service or not service.is_active or not service.salon.is_active or service.salon.owner_id != business.owner_id:
        return None
    if watch.listing_id and not public_agency_properties(business).filter(pk=watch.listing_id).exists():
        return None
    today = timezone.localdate()
    for offset in range(14):
        day = today + timedelta(days=offset)
        slots = get_available_slots(service.salon, day, service)
        if slots:
            slot = slots[0]
            title = watch.listing.titre if watch.listing_id else service.name
            command = f"BIEN {watch.listing_id} VISITE" if watch.listing_id else f"RDV {day.isoformat()} {slot:%H:%M}"
            return f"{day.isoformat()}T{slot:%H:%M}", [title, f"{day:%d/%m/%Y} à {slot:%H:%M}. Écris {command}"]
    return None


def watch_key(watch):
    return f"{watch.kind}:{watch.pk}:{watch.requested_at.isoformat()}"
