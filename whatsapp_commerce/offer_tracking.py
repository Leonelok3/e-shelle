"""Attribute WhatsApp activity to the public offer that started it."""

import re
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.utils import timezone

from business.models import BusinessProfile
from business.product_seo import offer_path
from immobilier_cameroun.agency import public_agency_properties
from whatsapp_agent.models import Campagne

from .models import BusinessWhatsAppConnection, BusinessWhatsAppMessage, WhatsAppOfferClick
from .services import normalize_phone

OFFER_SUFFIX = re.compile(r"\s*\[ES-([0-9a-f]{32})\]\s*$", re.IGNORECASE)
ORDER_WITHOUT_TITLE = re.compile(r"^commander(?:\s+(?:\d{1,3})\s*[x×])?[.!]?\s*$", re.IGNORECASE)
CATALOGUE_INTRO = "Bonjour, je souhaite des informations sur cette offre E-Shelle."
REFERENCE_LIFETIME = timedelta(days=7)
CONVERSATION_WINDOW = timedelta(hours=24)


def offer_connection(business):
    if (not getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False) or not business.is_published
            or business.is_trial or business.plan not in {BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM}):
        return None
    connection = BusinessWhatsAppConnection.objects.filter(
        business=business, status=BusinessWhatsAppConnection.Status.ACTIVE, agent_enabled=True,
        activation__isnull=False,
    ).select_related("activation").first()
    return connection if connection and normalize_phone(connection.display_phone_number) else None


def catalogue_offer_path(business, item_id):
    return offer_path(business.public_slug, item_id)


def campaign_offer_token(campaign, kind, offer_id):
    return signing.dumps({"campaign": campaign.pk, "kind": kind, "offer": offer_id}, salt="whatsapp-campaign-offer")


def _source_campaign(request, business_id, kind, offer_id):
    token = request.GET.get("campagne", "")[:512]
    if not token:
        return None
    try:
        data = signing.loads(token, salt="whatsapp-campaign-offer", max_age=90 * 86400)
    except signing.BadSignature:
        return None
    if data.get("kind") == kind and data.get("offer") == offer_id:
        return Campagne.objects.filter(pk=data.get("campaign"), business_id=business_id).first()
    return None


def offer_whatsapp_url(request, connection, *, message, item=None, listing=None):
    purposes = (request.headers.get("Sec-Purpose", "") + " " + request.headers.get("Purpose", "")).lower()
    if "prefetch" not in purposes and "prerender" not in purposes:
        click = WhatsAppOfferClick.objects.create(
            connection=connection, phone_number_id=connection.phone_number_id,
            catalog_item=item, property_listing=listing,
            campaign=_source_campaign(request, connection.business_id, "bien" if listing else "article", (listing or item).pk),
        )
        message = f"{message} [ES-{click.reference.hex}]"
    phone = normalize_phone(connection.display_phone_number).lstrip("+")
    return f"https://wa.me/{phone}?{urlencode({'text': message})}"


def claim_offer_click(connection, reference, entry_message):
    """Consume an opaque reference once, only on the receiving business number."""
    click = WhatsAppOfferClick.objects.select_related("catalog_item").filter(
        reference=reference, connection=connection, phone_number_id=connection.phone_number_id,
        entry_message__isnull=True, created_at__gte=timezone.now() - REFERENCE_LIFETIME,
    ).first()
    if not click or not connection.business.is_published:
        return
    if click.catalog_item_id:
        if not click.catalog_item.is_active or click.catalog_item.business_id != connection.business_id:
            return
    elif not public_agency_properties(connection.business).filter(pk=click.property_listing_id).exists():
        return
    WhatsAppOfferClick.objects.filter(pk=click.pk, entry_message__isnull=True).update(entry_message=entry_message)


def recent_offer_click(connection, entry_message):
    """Use only the latest link in this contact's message history at this point in the conversation."""
    return WhatsAppOfferClick.objects.filter(
        connection=connection, phone_number_id=connection.phone_number_id,
        entry_message__contact_id=entry_message.contact_id, entry_message_id__lte=entry_message.pk,
        entry_message__direction=BusinessWhatsAppMessage.Direction.INBOUND,
        entry_message__created_at__gte=entry_message.created_at - CONVERSATION_WINDOW,
    ).select_related("catalog_item", "entry_message").order_by("-entry_message_id").first()
