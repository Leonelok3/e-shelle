"""Agence inventory shared by public storefronts and the WhatsApp assistant."""

from urllib.parse import urlencode

from django.conf import settings
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessProfile
from whatsapp_commerce.models import BusinessWhatsAppConnection
from whatsapp_commerce.services import normalize_phone
from .models import Bien, StatutBien


def is_estate_agency(business):
    return (
        business.module == BusinessProfile.Module.IMMOBILIER
        and business.content_type_id is None
        and business.object_id is None
    )


def agency_profiles(owner_id):
    return BusinessProfile.objects.filter(
        owner_id=owner_id, module=BusinessProfile.Module.IMMOBILIER,
        is_active=True, content_type__isnull=True, object_id__isnull=True,
    )


def public_agency_properties(agence=None):
    listings = Bien.objects.filter(
        statut=StatutBien.PUBLIE,
        agence__module=BusinessProfile.Module.IMMOBILIER,
        agence__owner_id=F("proprietaire_id"),
        agence__content_type__isnull=True,
        agence__object_id__isnull=True,
    ).filter(Q(date_disponibilite__isnull=True) | Q(date_disponibilite__lte=timezone.localdate()))
    if agence is not None:
        return listings.filter(agence=agence, proprietaire_id=agence.owner_id)
    return listings.filter(agence__in=BusinessProfile.publicly_visible())


def property_url(bien):
    return settings.SITE_URL.rstrip("/") + bien.get_absolute_url()


def agency_whatsapp_url(bien):
    if not bien.agence_id or not public_agency_properties().filter(pk=bien.pk).exists():
        return ""
    phone = agency_assistant_phone(bien.agence_id)
    if not phone:
        return ""
    message = f"Bonjour, je souhaite des informations sur le BIEN {bien.pk}."
    return f"https://wa.me/{phone.lstrip('+')}?{urlencode({'text': message})}"


def agency_assistant_phone(agence_id):
    if not getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False):
        return ""
    connection = BusinessWhatsAppConnection.objects.filter(
        business_id=agence_id, status=BusinessWhatsAppConnection.Status.ACTIVE,
        business__plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        business__is_trial=False, agent_enabled=True, activation__isnull=False,
    ).only("display_phone_number").first()
    return normalize_phone(connection.display_phone_number) if connection else ""


def agency_contact_path(bien):
    return reverse("immobilier:whatsapp_bien", args=[bien.slug]) + "?source=profile"
