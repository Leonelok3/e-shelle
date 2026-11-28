"""Read public catalogue and agency facts owned by the campaign creator."""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from django.apps import apps
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile


@dataclass
class Offer:
    kind: str
    pk: int
    business: object
    title: str
    description: str
    price: str
    city: str
    path: str
    photos: list

    @property
    def key(self):
        return f"{self.kind}-{self.pk}"


def owned_offers(user, key=""):
    if not apps.is_installed("business"):
        return []
    from business.models import BusinessCatalogItem, BusinessProfile
    from business.product_seo import catalogue_price, catalogue_price_label, offer_path
    from immobilier_cameroun.agency import public_agency_properties
    from immobilier_cameroun.models import TypeTransaction

    profiles = BusinessProfile.publicly_visible().filter(owner=user).exclude(public_slug="")
    articles = BusinessCatalogItem.objects.filter(business__in=profiles, is_active=True).select_related("business")
    listings = public_agency_properties().filter(agence__in=profiles).select_related("agence")
    if key:
        kind, _, pk = key.partition("-")
        if kind not in {"article", "bien"} or not pk.isascii() or not pk.isdigit() or len(pk) > 18:
            return []
        articles = articles.filter(pk=pk) if kind == "article" else articles.none()
        listings = listings.filter(pk=pk) if kind == "bien" else listings.none()
    results = []
    for item in articles[:40]:
        label = item.price_label or item.price_label_en
        price = catalogue_price_label(label, catalogue_price(label)) or "Prix sur demande"
        photos = [item.image] + [photo.image for photo in item.images.all()[:3]] if key else []
        results.append(Offer("article", item.pk, item.business, item.display_title, item.display_description, price,
                             item.business.city, offer_path(item.business.public_slug, item.pk), photos))
    for listing in listings[:40]:
        price = listing.prix_formate
        if listing.type_transaction != TypeTransaction.VENTE and listing.periode_prix:
            price = f"{price} · {listing.get_periode_prix_display()}"
        results.append(Offer("bien", listing.pk, listing.agence, listing.titre, listing.description, price,
                             listing.ville, listing.get_absolute_url(),
                             [photo.image for photo in listing.photos.order_by("-est_photo_principale", "ordre")[:3]] if key else []))
    return results


def source_for(campaign):
    if not campaign.offer_id:
        return None
    return next(iter(owned_offers(campaign.user, f"{campaign.offer_kind}-{campaign.offer_id}")), None)


def copy_offer_photos(offer, campaign):
    photos = (photo for photo in offer.photos if photo)
    for name, photo in zip(("photo_produit", "photo_produit_2", "photo_produit_3"), photos):
        if getattr(campaign, name):
            continue
        with photo.open("rb") as stream:
            contents = stream.read(8 * 1024 * 1024 + 1)
        if len(contents) > 8 * 1024 * 1024:
            raise ValueError("Une photo de l’offre dépasse 8 Mo. Ajoute une photo plus légère dans AdGen.")
        setattr(campaign, name, ContentFile(contents, name=Path(photo.name).name))


def variant_url(offer, job):
    token = signing.dumps({"job": job.pk, "kind": offer.kind, "offer": offer.pk}, salt="adgen-offer-render")
    return settings.SITE_URL.rstrip("/") + offer.path + "?" + urlencode({"campagne": token})


def resolve_variant(token, business_id, kind, offer_id):
    from adgen.models import StudioUsage

    try:
        data = signing.loads(token, salt="adgen-offer-render", max_age=90 * 86400)
    except signing.BadSignature:
        return None
    if data.get("kind") != kind or data.get("offer") != offer_id:
        return None
    job = StudioUsage.objects.select_related("campaign", "campaign__user").filter(
        pk=data.get("job"), resource="video", status="consumed", campaign__offer_kind=kind, campaign__offer_id=offer_id,
    ).first()
    if job:
        offer = source_for(job.campaign)
        if offer and offer.business.pk == business_id:
            return job
    return None


def variant_summary(offer, jobs):
    from django.db.models import F
    from immobilier_cameroun.models import StatutVisite
    from salonhub.bookings.models import Appointment
    from whatsapp_commerce.checkout import verified_order_payment
    from whatsapp_commerce.models import BusinessWhatsAppBooking, WhatsAppDraftOrder, WhatsAppOfferClick

    variants = []
    for job in jobs.filter(status="consumed").select_related("campaign")[:12]:
        if not job.payload.get("video_url"):
            continue
        clicks = WhatsAppOfferClick.objects.filter(adgen_render=job, connection__business=offer.business)
        bookings = BusinessWhatsAppBooking.objects.filter(
            source_click__in=clicks, contact__business=offer.business,
            contact_id=F("source_click__entry_message__contact_id"),
            appointment__status__in=[Appointment.Status.CONFIRMED, Appointment.Status.DONE],
        )
        paid = 0
        if offer.kind == "bien":
            bookings = bookings.filter(property_visit__bien_id=offer.pk, property_visit__statut=StatutVisite.CONFIRME)
        else:
            bookings = bookings.filter(property_visit__isnull=True)
            paid = WhatsAppDraftOrder.objects.filter(
                source_click__in=clicks, business=offer.business, catalog_item_id=offer.pk,
                contact_id=F("source_click__entry_message__contact_id"), status=WhatsAppDraftOrder.Status.CONFIRMED,
                payment_transaction__commande_id=F("boutique_order__pk"),
            ).exclude(boutique_order__statut__in=["annulee", "remboursee"]).filter(verified_order_payment()).count()
        variants.append({
            "hook": job.payload.get("storyboard", {}).get("hook") or f"Version {job.pk}",
            "link": variant_url(offer, job) if job.campaign.prix == offer.price else "", "video": job.payload["video_url"],
            "conversations": clicks.filter(entry_message__isnull=False).values("entry_message__contact_id").distinct().count(),
            "paid": paid, "bookings": bookings.count(),
        })
    return variants
