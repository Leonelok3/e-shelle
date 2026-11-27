import datetime as dt
import json

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from salonhub.salons.models import Salon, Service
from .forms import AppointmentForm
from .utils import build_whatsapp_link, get_available_slots


@require_GET
def available_slots(request, slug):
    salon = get_object_or_404(Salon, slug=slug, is_active=True)
    date_str = request.GET.get("date")
    service_id = request.GET.get("service")
    try:
        date = dt.date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return JsonResponse({"error": "date invalide"}, status=400)

    service = None
    if service_id:
        service = Service.objects.filter(pk=service_id, salon=salon).first()

    slots = get_available_slots(salon, date, service)
    return JsonResponse({"slots": [s.strftime("%H:%M") for s in slots]})


@require_POST
@transaction.atomic
def create_appointment(request, slug):
    salon = get_object_or_404(Salon.objects.select_for_update(), slug=slug, is_active=True)
    form = AppointmentForm(request.POST)
    if form.is_valid():
        appointment = form.save(commit=False)
        appointment.salon = salon
        if appointment.service and (
            appointment.service.salon_id != salon.pk or not appointment.service.is_active
        ):
            messages.error(request, "Cette prestation n’est plus disponible.")
            return redirect(salon.get_absolute_url())
        if appointment.time not in get_available_slots(salon, appointment.date, appointment.service):
            messages.error(request, "Ce créneau n’est plus disponible.")
            return redirect(salon.get_absolute_url())
        appointment.save()
        wa_link = build_whatsapp_link(salon, appointment)
        return redirect(wa_link)
    messages.error(request, "Merci de vérifier les informations saisies.")
    return redirect(salon.get_absolute_url())
