from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import BusinessLeadEvent, BusinessProfile


MODULE_MODEL_MAP = {
    "gaz": ("gaz", "DepotGaz"),
    "resto": ("resto", "Restaurant"),
    "pressing": ("pressing", "Pressing"),
    "jobs": ("jobs", "OffreJob"),
    "sante_pro": ("sante", "ProfessionnelSante"),
    "sante_product": ("sante", "ProduitSante"),
}


def ensure_business_for_object(obj, module: str, defaults: dict | None = None) -> BusinessProfile:
    """Cree ou recupere le profil business global d'une fiche module."""
    defaults = defaults or {}
    content_type = ContentType.objects.get_for_model(obj.__class__)
    profile, created = BusinessProfile.objects.get_or_create(
        content_type=content_type,
        object_id=obj.pk,
        defaults={
            "module": module,
            "name": defaults.get("name") or _read_attr(obj, "name", "nom", "titre", default=str(obj)),
            "slug": _read_attr(obj, "slug", default=""),
            "city": defaults.get("city") or _related_name(obj, "city", "ville"),
            "district": defaults.get("district") or _related_name(obj, "neighborhood", "quartier"),
            "phone": defaults.get("phone") or _read_attr(obj, "phone", "telephone", default=""),
            "whatsapp": defaults.get("whatsapp") or _read_attr(obj, "whatsapp", default=""),
            "owner": defaults.get("owner") or _read_attr(obj, "owner", "gerant", default=None),
            "is_verified": bool(_read_attr(obj, "is_verified", default=False)),
            "is_active": bool(_read_attr(obj, "is_active", default=True)),
        },
    )
    if not created:
        changed = []
        sync_fields = {
            "name": defaults.get("name") or _read_attr(obj, "name", "nom", "titre", default=profile.name),
            "slug": _read_attr(obj, "slug", default=profile.slug),
            "city": defaults.get("city") or _related_name(obj, "city", "ville"),
            "district": defaults.get("district") or _related_name(obj, "neighborhood", "quartier"),
            "phone": defaults.get("phone") or _read_attr(obj, "phone", "telephone", default=profile.phone),
            "whatsapp": defaults.get("whatsapp") or _read_attr(obj, "whatsapp", default=profile.whatsapp),
            "is_verified": bool(_read_attr(obj, "is_verified", default=profile.is_verified)),
            "is_active": bool(_read_attr(obj, "is_active", default=profile.is_active)),
        }
        for field, value in sync_fields.items():
            if value is not None and getattr(profile, field) != value:
                setattr(profile, field, value)
                changed.append(field)
        if changed:
            changed.append("updated_at")
            profile.save(update_fields=changed)
    return profile


def create_tracking_event(
    business: BusinessProfile,
    event_type: str,
    target_url: str,
    source: str = "chat",
    metadata: dict | None = None,
) -> BusinessLeadEvent:
    return BusinessLeadEvent.objects.create(
        business=business,
        event_type=event_type,
        target_url=target_url,
        source=source,
        metadata=metadata or {},
    )


@transaction.atomic
def record_event_hit(event: BusinessLeadEvent, request=None) -> str:
    """Compte le clic puis retourne l'URL finale."""
    business = BusinessProfile.objects.select_for_update().get(pk=event.business_id)

    if event.event_type == BusinessLeadEvent.EventType.VIEW:
        business.views_count += 1
        fields = ["views_count", "updated_at"]
    elif event.event_type == BusinessLeadEvent.EventType.WHATSAPP:
        business.whatsapp_clicks += 1
        business.leads_count += 1
        fields = ["whatsapp_clicks", "leads_count", "updated_at"]
    elif event.event_type == BusinessLeadEvent.EventType.PHONE:
        business.phone_clicks += 1
        business.leads_count += 1
        fields = ["phone_clicks", "leads_count", "updated_at"]
    elif event.event_type == BusinessLeadEvent.EventType.DETAIL:
        business.detail_clicks += 1
        fields = ["detail_clicks", "updated_at"]
    else:
        business.leads_count += 1
        fields = ["leads_count", "updated_at"]

    business.save(update_fields=fields)
    if request:
        event.ip_address = _client_ip(request)
        event.user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
        event.save(update_fields=["ip_address", "user_agent"])
    return event.target_url or "/"


def build_tracked_actions(obj, module: str, urls: dict, source: str = "chat") -> dict:
    """Cree les evenements de tracking et retourne des URLs traquees."""
    profile = ensure_business_for_object(obj, module)
    tracked = {}
    event_map = {
        "primary_url": BusinessLeadEvent.EventType.WHATSAPP,
        "secondary_url": BusinessLeadEvent.EventType.PHONE,
        "url": BusinessLeadEvent.EventType.DETAIL,
    }
    for key, event_type in event_map.items():
        target = urls.get(key)
        if target:
            event = create_tracking_event(profile, event_type, target, source=source)
            tracked[key] = event.tracking_url()
    return tracked


@transaction.atomic
def record_provider_plan_payment(
    business: BusinessProfile,
    plan,
    paid_by,
    amount_xaf: int,
    payment_method: str = "OTHER",
):
    """
    Point d'integration paiement.
    A appeler quand un prestataire paie Pro/Business/Premium.
    Cree la transaction billing, active le plan business et genere la commission affilié.
    """
    from billing.affiliates import create_commission_for_transaction
    from billing.models import Transaction

    tx = Transaction.objects.create(
        user=paid_by,
        amount=amount_xaf,
        currency="XAF",
        type="CREDIT",
        status="COMPLETED",
        payment_method=payment_method,
        description=f"Abonnement prestataire E-Shelle - {plan.name}",
        metadata={
            "business_id": business.id,
            "business_name": business.name,
            "provider_plan": plan.code,
            "commission_base": str(amount_xaf),
            "product_type": "provider_subscription",
        },
    )
    business.activate_plan(plan.plan_level, plan.duration_days)
    business.ai_credits += plan.included_ai_credits
    if plan.included_boost_days:
        business.activate_boost(plan.included_boost_days)
    business.save(update_fields=["ai_credits", "updated_at"])
    create_commission_for_transaction(tx)
    return tx


def _read_attr(obj, *names, default=None):
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            return value() if callable(value) and name.startswith("get_") else value
    return default


def _related_name(obj, *names):
    for name in names:
        value = getattr(obj, name, None)
        if value is None:
            continue
        if isinstance(value, str):
            return value
        return getattr(value, "name", getattr(value, "nom", str(value)))
    return ""


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
