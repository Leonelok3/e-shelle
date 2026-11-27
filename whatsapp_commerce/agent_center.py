"""Business-owned workspace for setup, agent controls and pilot outcomes."""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from immobilier_cameroun.agency import is_estate_agency, public_agency_properties
from salonhub.bookings.models import Appointment

from .activation import activation_context
from .catalog_forwarding import receiver_number
from .checkout import checkout_enabled, verified_order_payment
from .entitlements import whatsapp_entitlements
from .follow_ups import booking_cases, payment_cases, review_cases
from .models import BusinessWhatsAppBooking, BusinessWhatsAppConnection, BusinessWhatsAppReplyJob, ScheduledBusinessWhatsAppMessage, WhatsAppCatalogChange, WhatsAppDraftOrder, WhatsAppOfferClick
from .views import _owned_business
from .voice import voice_available


def _results(business, since):
    clicks = WhatsAppOfferClick.objects.filter(connection__business=business, created_at__gte=since)
    paid = WhatsAppDraftOrder.objects.filter(
        business=business, status=WhatsAppDraftOrder.Status.CONFIRMED,
        confirmed_at__gte=since, payment_transaction__commande_id=F("boutique_order__pk"),
    ).exclude(boutique_order__statut__in=["annulee", "remboursee"]).filter(verified_order_payment())
    bookings = BusinessWhatsAppBooking.objects.filter(
        contact__business=business, appointment__created_at__gte=since,
        appointment__status__in=[Appointment.Status.CONFIRMED, Appointment.Status.DONE],
    )
    converted = set(paid.filter(source_click__in=clicks).values_list("contact_id", flat=True))
    converted.update(bookings.filter(source_click__in=clicks).values_list("contact_id", flat=True))
    contacts = clicks.filter(entry_message__isnull=False).values("entry_message__contact_id").distinct().count()
    return {
        "clicks": clicks.count(),
        "conversations": contacts, "converted": len(converted),
        "paid": paid.count(), "bookings": bookings.count(),
        "handoffs": BusinessWhatsAppReplyJob.objects.filter(
            message__contact__business=business, message__is_activation_test=False,
            message__created_at__gte=since, status=BusinessWhatsAppReplyJob.Status.REVIEW,
        ).count(),
        "failed": ScheduledBusinessWhatsAppMessage.objects.filter(
            contact__business=business, workflow__business=business, updated_at__gte=since,
            status=ScheduledBusinessWhatsAppMessage.Status.FAILED,
        ).count(),
    }


@login_required
@require_GET
@never_cache
def agent_center(request, business_id):
    business = _owned_business(request, business_id)
    eligible = whatsapp_entitlements(business)["can_use_crm"]
    connection = BusinessWhatsAppConnection.objects.filter(business=business).first()
    activation = activation_context(connection)
    setup = activation["setup"]
    estate = is_estate_agency(business)
    offers = (public_agency_properties(business) if estate else business.catalog_items.filter(is_active=True)).count()
    dashboard = reverse("whatsapp_commerce:business_dashboard", args=[business.pk])
    profile = reverse("business:business_edit", args=[business.pk])
    inventory = reverse("immobilier:mes_biens") if estate else reverse("business:catalog_manage", args=[business.pk])
    agenda = bool(setup and setup.booking_service_id)
    payment = checkout_enabled(business.pk)
    steps = [
        ("Publier la fiche", business.is_published, profile, "Vérifie les informations publiques et l’activation de la fiche."),
        ("Connecter le numéro WhatsApp Business", eligible and not activation["connection_blockers"], dashboard, " ".join(activation["connection_blockers"])),
        ("Ajouter la première offre", offers > 0, inventory, "Publie un bien disponible." if estate else "Ajoute un article ou importe une offre transférée."),
        ("Configurer les réponses de l’agent", not activation["setup_blockers"], dashboard + "#activation-agent", " ".join(activation["setup_blockers"])),
        ("Tester la conversation et activer l’agent", bool(setup and connection.agent_enabled and setup.activated_at and activation["test_ready"]), dashboard + "#activation-agent", "Fais le test associé à ce numéro, puis active les réponses."),
    ]
    if estate:
        steps.insert(4, ("Relier l’agenda des visites", agenda, dashboard + "#activation-agent", "Choisis une prestation de visite dans les réglages."))
    next_step = next((step for step in steps if not step[1]), None)
    return render(request, "whatsapp_commerce/agent_center.html", {
        "business": business, "eligible": eligible, "estate": estate, "dashboard": dashboard,
        "steps": steps, "done": sum(step[1] for step in steps), "next_step": next_step,
        "offers": offers, "inventory": inventory, "agenda": agenda, "payment": payment,
        "can_import": bool(receiver_number()), "voice_ready": bool(setup and setup.voice_enabled and voice_available()),
        "results": _results(business, timezone.now() - timedelta(days=7)),
        "open_cases": payment_cases(business).count() + booking_cases(business).count() + review_cases(business).count(),
    })


@login_required
@require_POST
def send_pilot_digest(request, business_id):
    business = _owned_business(request, business_id)
    email = request.user.email
    if not email:
        messages.error(request, "Renseigne ton adresse e-mail dans ton compte pour recevoir le récapitulatif.")
    else:
        totals = _results(business, timezone.now() - timedelta(days=7))
        link = settings.SITE_URL.rstrip("/") + reverse("whatsapp_commerce:agent_center", args=[business.pk])
        body = (f"{business.display_name} · 7 derniers jours\n\n"
                f"Clics sur les offres · {totals['clicks']}\nContacts issus des offres · {totals['conversations']}\n"
                f"Commandes confirmées et payées · {totals['paid']}\nRendez-vous confirmés · {totals['bookings']}\n"
                f"Messages transmis à l’équipe · {totals['handoffs']}\nÉchecs d’automatisation · {totals['failed']}\n\n{link}")
        sent = send_mail("Ton récapitulatif E‑Shelle", body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
        if sent:
            messages.success(request, "Récapitulatif envoyé à l’adresse de ton compte.")
        else:
            messages.error(request, "Le récapitulatif n’a pas pu être envoyé. Les chiffres restent disponibles ici.")
    return redirect("whatsapp_commerce:agent_center", business_id=business.pk)


@login_required
@require_GET
@never_cache
def catalog_history(request, business_id):
    business = _owned_business(request, business_id)
    rows = WhatsAppCatalogChange.objects.filter(business=business).order_by("-created_at", "-pk")
    return render(request, "whatsapp_commerce/catalog_history.html", {"business": business, "page": Paginator(rows, 30).get_page(request.GET.get("page"))})
