from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Exists, F, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_safe

from business.models import BusinessProfile
from business.product_seo import catalogue_offer_facts
from immobilier_cameroun.agency import is_estate_agency, public_agency_properties
from immobilier_cameroun.models import Bien, StatutVisite
from salonhub.bookings.models import Appointment

from .checkout import verified_order_payment
from .models import BusinessWhatsAppBooking, WhatsAppDraftOrder, WhatsAppOfferClick
from .offer_tracking import CATALOGUE_INTRO, catalogue_offer_path, offer_connection, offer_whatsapp_url


@require_safe
@never_cache
def catalogue_offer(request, public_slug, item_id):
    business = get_object_or_404(BusinessProfile.publicly_visible(), public_slug=public_slug)
    item = get_object_or_404(business.catalog_items, pk=item_id, is_active=True)
    return render(request, "whatsapp_commerce/catalogue_offer.html", {
        "business": business, "item": item,
        "can_contact": bool(offer_connection(business) or business.clean_whatsapp_number),
        "campaign_token": request.GET.get("campagne", "")[:512],
        "seo": catalogue_offer_facts(business, item),
    })


@require_GET
@never_cache
def catalogue_offer_whatsapp(request, public_slug, item_id):
    business = get_object_or_404(BusinessProfile.publicly_visible(), public_slug=public_slug)
    item = get_object_or_404(business.catalog_items, pk=item_id, is_active=True)
    message = f"{CATALOGUE_INTRO}\n{item.title}"
    connection = offer_connection(business)
    if connection:
        return redirect(offer_whatsapp_url(request, connection, message=message, item=item))
    return redirect(business.whatsapp_url(message) or catalogue_offer_path(business, item.pk))


def _counts(rows, key):
    return {row[key]: row["total"] for row in rows.order_by().values(key).annotate(total=Count("pk"))}


def _report_rows(request, business, offers, *, estate=False):
    key = "property_listing_id" if estate else "catalog_item_id"
    page = Paginator(offers, 25).get_page(request.GET.get("biens" if estate else "articles"))
    ids = [offer.pk for offer in page]
    clicks = WhatsAppOfferClick.objects.filter(connection__business=business, **{f"{key}__in": ids})
    activity = {row[key]: row for row in clicks.order_by().values(key).annotate(
        clicks=Count("pk"), conversations=Count("entry_message__contact", distinct=True),
    )}
    bookings = BusinessWhatsAppBooking.objects.filter(
        source_click__in=clicks, contact__business=business,
        contact_id=F("source_click__entry_message__contact_id"),
        appointment__status__in=[Appointment.Status.CONFIRMED, Appointment.Status.DONE],
    )
    if estate:
        bookings = bookings.filter(property_visit__statut=StatutVisite.CONFIRME, property_visit__bien_id=F("source_click__property_listing_id"))
    else:
        bookings = bookings.filter(property_visit__isnull=True)
    confirmed = _counts(bookings, f"source_click__{key}")
    paid = {}
    if not estate:
        orders = WhatsAppDraftOrder.objects.filter(
            source_click__in=clicks, business=business, status=WhatsAppDraftOrder.Status.CONFIRMED,
            catalog_item_id=F("source_click__catalog_item_id"), contact_id=F("source_click__entry_message__contact_id"),
            payment_transaction__commande_id=F("boutique_order__pk"),
        ).exclude(boutique_order__statut="annulee").filter(verified_order_payment())
        paid = _counts(orders, f"source_click__{key}")
    for offer in page:
        offer.click_count = activity.get(offer.pk, {}).get("clicks", 0)
        offer.conversation_count = activity.get(offer.pk, {}).get("conversations", 0)
        offer.booking_count = confirmed.get(offer.pk, 0)
        offer.paid_count = paid.get(offer.pk, 0)
        if business.is_published and offer.shareable:
            path = offer.get_absolute_url() if estate else catalogue_offer_path(business, offer.pk)
            offer.share_url = request.build_absolute_uri(path)
    return page


@login_required
@require_GET
@never_cache
def offer_report(request, business_id):
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    items = business.catalog_items.order_by("-is_active", "order", "pk").annotate(shareable=F("is_active"))
    listings = None
    if is_estate_agency(business):
        listings = Bien.objects.filter(agence=business, proprietaire_id=business.owner_id).order_by("-created_at", "-pk")
        listings = listings.annotate(shareable=Exists(public_agency_properties(business).filter(pk=OuterRef("pk"))))
    return render(request, "whatsapp_commerce/offer_report.html", {
        "business": business, "tracking_ready": bool(offer_connection(business)),
        "items": _report_rows(request, business, items),
        "listings": _report_rows(request, business, listings, estate=True) if listings is not None else None,
    })
