import datetime as dt
from urllib.parse import quote

from .models import Appointment


def get_available_slots(salon, date, service=None, slot_step=30):
    """Retourne la liste des heures (datetime.time) disponibles pour un salon
    à une date donnée, en tenant compte des horaires d'ouverture et des
    rendez-vous déjà pris (statut en attente ou confirmé)."""
    weekday = date.weekday()
    try:
        hours = salon.opening_hours.get(weekday=weekday)
    except salon.opening_hours.model.DoesNotExist:
        return []

    if hours.is_closed:
        return []

    duration = service.duration_minutes if service else slot_step

    slots = []
    current = dt.datetime.combine(date, hours.start_time)
    end = dt.datetime.combine(date, hours.end_time)

    while current + dt.timedelta(minutes=duration) <= end:
        slots.append(current.time())
        current += dt.timedelta(minutes=slot_step)

    # retire les créneaux déjà passés si c'est aujourd'hui
    now = dt.datetime.now()
    if date == now.date():
        slots = [s for s in slots if dt.datetime.combine(date, s) > now]

    # retire les créneaux déjà réservés
    taken = set(
        Appointment.objects.filter(
            salon=salon, date=date,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        ).values_list("time", flat=True)
    )
    slots = [s for s in slots if s not in taken]
    return slots


def build_whatsapp_link(salon, appointment):
    """Construit le lien wa.me pré-rempli pour confirmer le rendez-vous."""
    service_name = appointment.service.name if appointment.service else "Prestation à définir"
    message = (
        f"Bonjour {salon.name} 👋,\n"
        f"Je souhaite confirmer mon rendez-vous pris via SalonHub :\n\n"
        f"Prestation : {service_name}\n"
        f"Date : {appointment.date.strftime('%d/%m/%Y')}\n"
        f"Heure : {appointment.time.strftime('%H:%M')}\n"
        f"Nom : {appointment.client_name}\n"
        f"Téléphone : {appointment.client_phone}\n\n"
        f"Merci de me confirmer la disponibilité 🙏"
    )
    return f"https://wa.me/{salon.whatsapp_number}?text={quote(message)}"
