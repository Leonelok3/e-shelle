"""WhatsApp booking commands using the shared SalonHub agenda."""

import re
from datetime import date, time, timedelta

from django.db import transaction
from django.utils import timezone

from immobilier_cameroun.agency import public_agency_properties
from immobilier_cameroun.models import DemandeVisite, StatutVisite
from salonhub.bookings.models import Appointment
from salonhub.bookings.utils import get_available_slots
from salonhub.salons.models import Salon, Service

from .models import BusinessWhatsAppBooking

COMMAND = re.compile(r"^(?:RDV|REPORTER\s+(?P<ref>\d{1,12}))\s+(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2})$", re.I)
BOOKING_WORDS = re.compile(r"\b(rdv|rendez-vous|rendez vous|r[ée]serv(?:er|ation)|cr[ée]neaux?|reporter|visites?|visiter)\b", re.I)
HORIZON = 14


def owner_services(owner_id):
    return Service.objects.filter(is_active=True, salon__is_active=True, salon__owner_id=owner_id)


def _suggest_slots(service, listing=None):
    today = timezone.localdate()
    choices = []
    for offset in range(HORIZON):
        day = today + timedelta(days=offset)
        for slot in get_available_slots(service.salon, day, service)[:2]:
            choices.append(f"• RDV {day.isoformat()} {slot:%H:%M}")
        if len(choices) >= 3:
            break
    if not choices:
        return "Aucun créneau disponible dans les deux prochaines semaines. Demande à l’équipe un autre créneau."
    subject = listing.titre if listing else service.name
    return (
        f"Créneaux pour {subject} ({timezone.get_current_timezone_name()}). "
        "Pour réserver, renvoie une ligne ci-dessous. Pour reporter un rendez-vous, remplace RDV par REPORTER suivi de ta référence.\n"
        + "\n".join(choices[:4])
    )


@transaction.atomic
def _book(service, contact, day, slot, reference, *, listing=None, estate=False):
    salon = Salon.objects.select_for_update().filter(
        pk=service.salon_id, owner_id=contact.business.owner_id, is_active=True,
    ).first()
    if salon is None:
        return ""
    today = timezone.localdate()
    if not today <= day < today + timedelta(days=HORIZON):
        return "Choisis un créneau dans les deux prochaines semaines et écris RDV pour voir les disponibilités."
    appointment = None
    if reference:
        booking = BusinessWhatsAppBooking.objects.filter(
            appointment_id=reference, contact=contact, appointment__salon=salon,
            appointment__status=Appointment.Status.CONFIRMED,
            property_visit__isnull=not estate,
        ).select_related("appointment__service", "property_visit__bien").first()
        if booking is None:
            return "Rendez-vous introuvable dans cette conversation. Vérifie la référence."
        appointment = booking.appointment
        now = timezone.localtime()
        if (appointment.date, appointment.time) <= (now.date(), now.time()):
            return "Ce rendez-vous est passé. Écris RDV pour prendre un nouveau créneau."
        service = appointment.service
        if service is None or not service.is_active:
            return ""
        if estate:
            listing = booking.property_visit.bien
    if estate:
        listing_id = getattr(listing, "pk", None)
        if not public_agency_properties(contact.business).select_for_update(of=("self",)).filter(pk=listing_id).first():
            return "Ce bien n’est plus proposé. Écris BIENS pour reprendre la recherche ou contacte l’agence."
    if not appointment:
        existing = BusinessWhatsAppBooking.objects.filter(
            contact=contact, appointment__salon=salon, appointment__date=day, appointment__time=slot,
            appointment__status=Appointment.Status.CONFIRMED,
        ).filter(**({"property_visit__bien": listing} if estate else {"property_visit__isnull": True})).first()
        if existing:
            return _confirmation(existing.appointment, "confirmé", listing)
    if slot not in get_available_slots(salon, day, service, exclude_appointment=getattr(appointment, "pk", None)):
        return "Ce créneau n’est plus disponible. Écris RDV pour voir les créneaux libres."
    if appointment:
        appointment.date, appointment.time = day, slot
        appointment.save(update_fields=["date", "time"])
        if estate:
            booking.property_visit.date_souhaitee = day
            booking.property_visit.message = f"Visite confirmée via WhatsApp à {slot:%H:%M}."
            booking.property_visit.save(update_fields=["date_souhaitee", "message"])
        return _confirmation(appointment, "reporté", listing)
    appointment = Appointment.objects.create(
        salon=salon, service=service, date=day, time=slot,
        client_name=(contact.display_name or contact.phone)[:150],
        client_phone=contact.phone, status=Appointment.Status.CONFIRMED,
    )
    property_visit = None
    if estate:
        property_visit = DemandeVisite.objects.create(
            bien=listing, nom_complet=appointment.client_name, telephone=contact.phone,
            date_souhaitee=day, statut=StatutVisite.CONFIRME, message=f"Visite confirmée via WhatsApp à {slot:%H:%M}.",
        )
    BusinessWhatsAppBooking.objects.create(appointment=appointment, contact=contact, property_visit=property_visit)
    return _confirmation(appointment, "confirmé", listing)


def _confirmation(appointment, status, listing=None):
    subject = f"Visite {status}e pour {listing.titre}" if listing else f"Rendez-vous {status}"
    return (
        f"{subject} le {appointment.date:%d/%m/%Y} à {appointment.time:%H:%M}. "
        f"Référence : {appointment.pk}. Pour le reporter, écris REPORTER {appointment.pk} AAAA-MM-JJ HH:MM."
    )


def booking_reply(activation, contact, body, *, typed=True, listing=None, estate=False):
    if not activation.booking_service_id or not BOOKING_WORDS.search(body):
        return None
    service = owner_services(contact.business.owner_id).select_related("salon").filter(
        pk=activation.booking_service_id,
    ).first()
    if service is None:
        return ""
    command = COMMAND.fullmatch(body.strip()) if typed else None
    if estate and listing is None and (command is None or not command["ref"]):
        return "Choisis d’abord le bien à visiter en envoyant BIEN suivi de sa référence."
    if command is None:
        return _suggest_slots(service, listing)
    try:
        day, slot = date.fromisoformat(command["date"]), time.fromisoformat(command["time"])
    except ValueError:
        return "Date ou heure invalide. Écris RDV pour voir les créneaux disponibles."
    return _book(service, contact, day, slot, command["ref"], listing=listing, estate=estate)
