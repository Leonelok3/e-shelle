from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from business.models import BusinessCatalogItem, BusinessProfile

from ..models import LiveBooking


PAID_BOOKING_STATUSES = {
    LiveBooking.Statut.VALIDEE_ADMIN,
    LiveBooking.Statut.CONFIRMEE,
    LiveBooking.Statut.TERMINEE,
}


def _get_or_create_business_profile(booking):
    profile = booking.business_profile
    if profile:
        if booking.user_id and profile.owner_id not in (None, booking.user_id):
            raise ValidationError("Le profil E-Shelle lié appartient à un autre compte.")
        if booking.user_id and profile.owner_id is None:
            profile.owner = booking.user
            profile.save(update_fields=["owner", "updated_at"])
        return profile

    profile = BusinessProfile.objects.create(
        owner=booking.user,
        module=BusinessProfile.Module.BOUTIQUE,
        name=booking.nom_entreprise,
        slug=slugify(f"ocd-{booking.code_reservation}"),
        phone=booking.telephone_whatsapp,
        whatsapp=booking.telephone_whatsapp,
        description=booking.description_activite,
        plan=BusinessProfile.Plan.FREE,
        activation_status=BusinessProfile.ActivationStatus.ACTIVE,
        is_active=True,
    )
    booking.business_profile = profile
    booking.save(update_fields=["business_profile", "date_mise_a_jour"])
    return profile


def _sync_live_catalog(booking, profile):
    existing_titles = set(profile.catalog_items.values_list("title", flat=True))
    limit = profile.catalog_item_limit
    remaining = None if limit is None else max(limit - len(existing_titles), 0)

    for product in booking.produits_catalogue.filter(est_disponible=True):
        if product.nom in existing_titles:
            continue
        if remaining == 0:
            break
        BusinessCatalogItem.objects.create(
            business=profile,
            item_type=BusinessCatalogItem.ItemType.PRODUCT,
            title=product.nom,
            description=product.description,
            price_label=product.prix_formate,
            image=product.image if product.image else None,
            is_active=True,
        )
        existing_titles.add(product.nom)
        if remaining is not None:
            remaining -= 1


def ensure_business_profile_for_live(booking):
    if not booking.is_payment_validated:
        raise ValidationError("Le profil E-Shelle sera créé après validation du paiement.")

    profile = _get_or_create_business_profile(booking)
    _sync_live_catalog(booking, profile)
    return profile


@transaction.atomic
def confirm_live_booking_payment(booking_id):
    booking = LiveBooking.objects.select_for_update().select_related(
        "package", "user", "business_profile"
    ).get(pk=booking_id)

    if not (booking.preuve_paiement or booking.reference_paiement):
        raise ValidationError("Ajoutez une preuve ou une référence de paiement avant de confirmer.")

    if booking.statut not in PAID_BOOKING_STATUSES:
        booking.statut = LiveBooking.Statut.VALIDEE_ADMIN

    if booking.payment_validated_at:
        profile = _get_or_create_business_profile(booking)
        _sync_live_catalog(booking, profile)
    else:
        profile = _get_or_create_business_profile(booking)
        profile.is_verified = True
        if booking.is_marathon_vip:
            profile.activate_plan(BusinessProfile.Plan.PREMIUM, days=30, ai_credits=50)
            profile.activate_boost(days=15)
            profile.is_verified = True
            profile.save(update_fields=["is_verified", "updated_at"])
        else:
            profile.save(update_fields=["is_verified", "updated_at"])
        _sync_live_catalog(booking, profile)
        booking.payment_validated_at = timezone.now()

    booking.boutique_active = True
    booking.save(update_fields=[
        "statut",
        "payment_validated_at",
        "boutique_active",
        "date_mise_a_jour",
    ])
    return booking


def get_live_vendor_ecosystem_links(booking):
    links = {
        "boutique_url": reverse("ocd_live:boutique", kwargs={"code": booking.code_reservation}),
        "business_public_url": "",
        "business_dashboard_url": "",
        "waba_connect_url": "",
        "waba_inbox_url": "",
        "waba_campaigns_url": "",
        "waba_campaign_create_url": "",
        "is_marathon_vip": booking.is_payment_validated and booking.is_marathon_vip,
        "business_profile": None,
    }

    if not booking.is_payment_validated or not booking.business_profile:
        return links

    profile = booking.business_profile
    links["business_profile"] = profile
    links["business_public_url"] = profile.public_url
    if booking.user_id and profile.owner_id == booking.user_id:
        links["business_dashboard_url"] = reverse("business:dashboard")

    if not (booking.is_marathon_vip and profile.owner_id):
        return links

    from whatsapp_commerce.entitlements import whatsapp_entitlements

    if not whatsapp_entitlements(profile)["can_connect"]:
        return links

    links.update({
        "waba_connect_url": reverse(
            "whatsapp_commerce:business_connect",
            kwargs={"business_id": profile.id},
        ),
        "waba_inbox_url": reverse("whatsapp_commerce:inbox"),
        "waba_campaigns_url": reverse(
            "whatsapp_commerce:business_campaigns",
            kwargs={"business_id": profile.id},
        ),
        "waba_campaign_create_url": reverse(
            "whatsapp_commerce:business_campaign_create",
            kwargs={"business_id": profile.id},
        ),
    })
    return links
