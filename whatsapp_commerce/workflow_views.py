from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from boutique.models import Commande
from salonhub.bookings.models import Appointment

from .automations import _find_approved_template
from .checkout import verified_order_payment
from .entitlements import require_whatsapp_entitlement
from .models import BusinessWhatsAppConnection, BusinessWhatsAppWorkflow, ScheduledBusinessWhatsAppMessage
from .onboarding import MetaOnboardingError
from .views import _owned_business
from .workflows import BUTTONS, PARAMETERS, Kind, _bookings, _orders, appointment_at, booking_subject, validate_workflow_template


def _eligible_deliveries(business):
    return _orders(business).filter(boutique_order__statut__in=["en_attente", "payee"]).filter(
        Q(boutique_order__statut="payee") | verified_order_payment(),
    ).exclude(payment_transaction__statut="rembourse")


def _save_rule(request, business):
    kind = request.POST.get("kind", "")
    if kind not in Kind.values:
        raise Http404
    if request.POST.get("action") == "pause":
        rule = BusinessWhatsAppWorkflow.objects.filter(business=business, kind=kind).first()
        if rule and rule.enabled:
            rule.enabled = False
            rule.save(update_fields=["enabled", "updated_at"])
        messages.success(request, "Automatisation mise en pause.")
        return
    name = request.POST.get("template", "").strip()
    language = request.POST.get("language", "").strip()
    try:
        hours = int(request.POST.get("delay", ""))
        minimum = 0 if kind == Kind.SHIPPING else 1
        if not minimum <= hours <= 168 or not 1 <= len(name) <= 128 or not 2 <= len(language) <= 32:
            raise ValueError
        validate_workflow_template(kind, _find_approved_template(business, name, language))
    except ValueError:
        messages.error(request, "Renseigne un modèle, sa langue et un délai valide pour cette automatisation.")
        return
    except MetaOnboardingError as exc:
        messages.error(request, str(exc))
        return
    BusinessWhatsAppWorkflow.objects.update_or_create(business=business, kind=kind, defaults={
        "template_name": name, "template_language": language, "delay_hours": hours, "enabled": True,
    })
    messages.success(request, "Automatisation activée avec ce modèle et ce délai.")


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def business_workflows(request, business_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_automate"):
        return redirect("tarifs")
    if request.method == "POST":
        _save_rule(request, business)
        return redirect("whatsapp_commerce:business_workflows", business_id=business.pk)
    rules = {rule.kind: rule for rule in BusinessWhatsAppWorkflow.objects.filter(business=business)}
    now = timezone.now()
    bookings = _bookings(business).filter(
        appointment__status=Appointment.Status.CONFIRMED,
        appointment__date__gte=timezone.localdate(now - timedelta(days=7)), appointment__date__lte=timezone.localdate(now),
    ).order_by("-appointment__date", "-appointment__time")
    completed = []
    for booking in bookings[:40]:
        if _booking_ended(booking, now):
            booking.subject = booking_subject(booking)
            completed.append(booking)
    return render(request, "whatsapp_commerce/workflows.html", {
        "business": business,
        "rules": [(kind, label, rules.get(kind), PARAMETERS[kind], [button for _, button in BUTTONS[kind]]) for kind, label in Kind.choices],
        "history": ScheduledBusinessWhatsAppMessage.objects.filter(
            workflow__business=business, connection__business=business, contact__business=business,
        ).select_related("workflow", "contact", "workflow_booking__appointment", "workflow_order__boutique_order").order_by("-created_at")[:50],
        "ready": getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False) and BusinessWhatsAppConnection.objects.filter(
            business=business, status=BusinessWhatsAppConnection.Status.ACTIVE, automations_enabled=True,
        ).exists(),
        "completed_candidates": completed[:10],
        "delivery_candidates": _eligible_deliveries(business).order_by("-confirmed_at")[:10],
    })


def _booking_ended(booking, now):
    service = booking.appointment.service
    return appointment_at(booking) + timedelta(minutes=service.duration_minutes if service else 0) <= now


@login_required
@require_POST
@transaction.atomic
def record_workflow_completion(request, business_id, subject, record_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_automate"):
        return redirect("tarifs")
    now = timezone.now()
    if subject == "booking":
        booking = get_object_or_404(_bookings(business), pk=record_id)
        appointment = Appointment.objects.select_for_update().get(pk=booking.appointment_id)
        booking.appointment = appointment
        if appointment.status == Appointment.Status.CONFIRMED and _booking_ended(booking, now):
            appointment.status = Appointment.Status.DONE
            appointment.save(update_fields=["status"])
    elif subject == "order":
        draft = get_object_or_404(_orders(business), pk=record_id)
        order = Commande.objects.select_for_update().get(pk=draft.boutique_order.pk)
        if _eligible_deliveries(business).filter(pk=draft.pk).exists():
            order.statut = "livree"
            order.save(update_fields=["statut", "updated_at"])
    else:
        raise Http404
    return redirect("whatsapp_commerce:business_workflows", business_id=business.pk)
