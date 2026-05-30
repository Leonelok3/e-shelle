from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import BusinessLeadEvent, BusinessProfile


MODULE_MODEL_MAP = {
    "gaz": ("gaz", "DepotGaz"),
    "resto": ("resto", "Restaurant"),
    "pressing": ("pressing", "Pressing"),
    "jobs": ("jobs", "OffreJob"),
    "sante_pro": ("sante", "ProfessionnelSante"),
    "sante_product": ("sante", "ProduitSante"),
    "annonces": ("annonces_cam", "ProfilVendeur"),
    "market": ("annonces_cam", "ProfilVendeur"),
    "agro": ("agro", "ActeurAgro"),
    "services": ("artisans", "ProfilArtisan"),
}

MODULE_ALIASES = {
    "sante_pro": BusinessProfile.Module.SANTE,
    "sante_product": BusinessProfile.Module.SANTE,
    "annonces": BusinessProfile.Module.MARKET,
    "market": BusinessProfile.Module.MARKET,
    "tibo": BusinessProfile.Module.BOUTIQUE,
    "artisans": BusinessProfile.Module.SERVICES,
}


def ensure_business_for_object(obj, module: str, defaults: dict | None = None) -> BusinessProfile:
    """Cree ou recupere le profil business global d'une fiche module."""
    defaults = defaults or {}
    module = _normalize_module(module)
    content_type = ContentType.objects.get_for_model(obj.__class__)
    profile, created = BusinessProfile.objects.get_or_create(
        content_type=content_type,
        object_id=obj.pk,
        defaults={
            "module": module,
            "name": defaults.get("name") or _read_attr(obj, "name", "nom", "titre", default=str(obj)),
            "slug": _read_attr(obj, "slug", default=""),
            "public_slug": defaults.get("public_slug") or "",
            "city": defaults.get("city") or _related_name(obj, "city", "ville"),
            "district": defaults.get("district") or _related_name(obj, "neighborhood", "quartier"),
            "phone": defaults.get("phone") or _read_attr(obj, "phone", "telephone", default=""),
            "whatsapp": defaults.get("whatsapp") or _read_attr(obj, "whatsapp", default=""),
            "owner": defaults.get("owner") or _read_attr(obj, "owner", "gerant", default=None),
            "description": defaults.get("description") or _read_attr(obj, "description", default=""),
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
            "owner": defaults.get("owner") or _read_attr(obj, "owner", "gerant", default=profile.owner),
            "description": defaults.get("description") or _read_attr(obj, "description", default=profile.description),
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


def _normalize_module(module: str) -> str:
    module = (module or BusinessProfile.Module.GENERAL).strip()
    if module in MODULE_ALIASES:
        return MODULE_ALIASES[module]
    valid = {choice[0] for choice in BusinessProfile.Module.choices}
    return module if module in valid else BusinessProfile.Module.GENERAL


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


def record_business_impression(
    business: BusinessProfile,
    source: str = "chat",
    metadata: dict | None = None,
) -> None:
    """Compte une vue quand une fiche business est affichee dans l'agent."""
    event = create_tracking_event(
        business,
        BusinessLeadEvent.EventType.VIEW,
        "",
        source=source,
        metadata=metadata or {},
    )
    record_event_hit(event)


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


def build_tracked_actions(
    obj,
    module: str,
    urls: dict,
    source: str = "chat",
    metadata: dict | None = None,
    record_view: bool = False,
) -> dict:
    """Cree les evenements de tracking et retourne des URLs traquees."""
    profile = ensure_business_for_object(obj, module)
    if record_view:
        record_business_impression(profile, source=source, metadata=metadata)

    tracked = {}
    event_map = {
        "primary_url": BusinessLeadEvent.EventType.WHATSAPP,
        "secondary_url": BusinessLeadEvent.EventType.PHONE,
        "url": BusinessLeadEvent.EventType.DETAIL,
    }
    for key, event_type in event_map.items():
        target = urls.get(key)
        if target:
            event = create_tracking_event(profile, event_type, target, source=source, metadata=metadata)
            tracked[key] = event.tracking_url()
    return tracked


def collect_business_items(business: BusinessProfile, limit: int = 24) -> list[dict]:
    """Retourne les produits/services/offres affichables sur la vitrine publique."""
    obj = business.content_object
    if not obj:
        return []

    model_name = obj.__class__.__name__
    if model_name == "ActeurAgro":
        return _items_agro_actor(obj, business, limit)
    if model_name == "ProfilVendeur":
        return _items_market_seller(obj, limit)
    if model_name == "Annonce":
        return [_item_announcement(obj)]
    if model_name == "Restaurant":
        return _items_restaurant(obj, limit)
    if model_name == "Pressing":
        return _items_pressing(obj, limit)
    if model_name == "DepotGaz":
        return _items_gaz_depot(obj)
    if model_name == "ProfessionnelSante":
        return _items_sante_pro(obj, business, limit)
    if model_name == "ProduitSante":
        return [_item_sante_product(obj)]
    if model_name == "OffreJob":
        return [_item_job_offer(obj)]
    if model_name == "ProfilArtisan":
        return _items_artisan(obj, limit)
    if model_name == "Vehicule":
        return [_item_direct_listing(obj, "Vehicule", "Auto")]
    if model_name == "Bien":
        return [_item_direct_listing(obj, "Bien immobilier", "Immobilier")]
    if model_name == "Product":
        return [_item_tibo_product(obj)]
    return []


def _items_agro_actor(actor, business, limit):
    try:
        from agro.models import ProduitAgro
    except Exception:
        return []
    qs = (
        ProduitAgro.objects.filter(acteur=actor, statut="publie")
        .select_related("categorie")
        .order_by("-date_creation")[:limit]
    )
    return [
        {
            "type": "Produit agro",
            "title": p.nom,
            "description": p.description[:140],
            "price": _money(p.prix_unitaire, getattr(p, "devise", "XAF"), suffix=f"/{getattr(p, 'unite_mesure', '')}".rstrip("/")),
            "image": _image_url(p, "image_principale"),
            "url": _safe_url(p),
            "contact_url": business.whatsapp_url(f"Bonjour {business.name}, je suis interesse par {p.nom} vu sur E-Shelle."),
            "meta": getattr(p.categorie, "nom", ""),
        }
        for p in qs
    ]


def _items_market_seller(profile, limit):
    try:
        from annonces_cam.models import Annonce
    except Exception:
        return []
    qs = Annonce.objects.actives_du_vendeur(profile.user).order_by("-est_mise_en_avant", "-date_publication")[:limit]
    items = []
    for annonce in qs:
        photo = annonce.photo_principale()
        items.append(
            {
                "type": "Annonce",
                "title": annonce.titre,
                "description": annonce.description[:140],
                "price": annonce.prix_formate,
                "image": _image_url(photo, "image") if photo else "",
                "url": _safe_url(annonce),
                "contact_url": annonce.get_whatsapp_url(),
                "meta": annonce.ville,
            }
        )
    return items


def _item_announcement(annonce):
    photo = getattr(annonce, "photo_principale", None)
    if callable(photo):
        photo = photo()
    return {
        "type": "Annonce",
        "title": annonce.titre,
        "description": annonce.description[:140],
        "price": annonce.prix_formate,
        "image": _image_url(photo, "image") if photo else "",
        "url": _safe_url(annonce),
        "contact_url": annonce.get_whatsapp_url(),
        "meta": annonce.ville,
    }


def _items_restaurant(restaurant, limit):
    qs = restaurant.dishes.filter(is_active=True).select_related("category").order_by("-is_popular", "order", "name")[:limit]
    return [
        {
            "type": "Plat",
            "title": dish.name,
            "description": dish.description,
            "price": dish.formatted_price,
            "image": _image_url(dish, "image"),
            "url": reverse("resto:restaurant_detail", kwargs={"slug": restaurant.slug}),
            "contact_url": restaurant.whatsapp_url(dish.name),
            "meta": getattr(dish.category, "name", ""),
        }
        for dish in qs
    ]


def _items_pressing(pressing, limit):
    qs = pressing.services.filter(disponible=True).select_related("categorie").order_by("ordre", "nom")[:limit]
    return [
        {
            "type": "Service pressing",
            "title": service.nom,
            "description": getattr(service.categorie, "nom", "") or "Service disponible",
            "price": service.prix_display,
            "image": _image_url(pressing, "photo"),
            "url": reverse("pressing:detail", kwargs={"slug": pressing.slug}),
            "contact_url": pressing.whatsapp_commande_url(f"{service.nom} x1"),
            "meta": service.get_unite_display(),
        }
        for service in qs
    ]


def _items_gaz_depot(depot):
    items = []
    prices = [("Bouteille 6 kg", depot.prix_6kg), ("Bouteille 12 kg", depot.prix_12kg), ("Bouteille 15 kg", depot.prix_15kg)]
    for title, price in prices:
        if not price:
            continue
        items.append(
            {
                "type": "Gaz",
                "title": title,
                "description": depot.description or "Commande de gaz avec contact direct.",
                "price": f"{price:,} FCFA".replace(",", " "),
                "image": _image_url(depot, "photo"),
                "url": reverse("gaz:detail", kwargs={"slug": depot.slug}),
                "contact_url": depot.whatsapp_url,
                "meta": getattr(depot.ville, "nom", ""),
            }
        )
    if not items:
        items.append(
            {
                "type": "Service gaz",
                "title": "Commande de gaz",
                "description": depot.description or "Contactez le depot pour verifier les prix et la disponibilite.",
                "price": "Prix a confirmer",
                "image": _image_url(depot, "photo"),
                "url": reverse("gaz:detail", kwargs={"slug": depot.slug}),
                "contact_url": depot.whatsapp_url,
                "meta": getattr(depot.ville, "nom", ""),
            }
        )
    return items


def _items_sante_pro(pro, business, limit):
    try:
        from sante.models import ProduitSante
    except Exception:
        return []
    qs = ProduitSante.objects.filter(is_active=True)
    if pro.auteur_id:
        qs = qs.filter(auteur=pro.auteur)
    else:
        qs = qs.filter(telephone=pro.telephone)
    qs = qs.order_by("-is_featured", "-created_at")[:limit]
    items = [_item_sante_product(product) for product in qs]
    if items:
        return items
    return [
        {
            "type": "Service sante",
            "title": pro.get_type_pro_display(),
            "description": pro.description or "Contactez ce professionnel de sante depuis E-Shelle.",
            "price": "Sur rendez-vous",
            "image": "",
            "url": reverse("sante:detail_professionnel", kwargs={"slug": pro.slug}),
            "contact_url": business.whatsapp_url(),
            "meta": getattr(pro.ville, "nom", ""),
        }
    ]


def _item_sante_product(product):
    return {
        "type": "Produit sante",
        "title": product.titre,
        "description": product.description[:140],
        "price": product.prix_display,
        "image": _image_url(product, "image"),
        "url": _safe_url(product),
        "contact_url": product.commande_whatsapp_url,
        "meta": getattr(product.ville, "nom", ""),
    }


def _item_job_offer(offer):
    return {
        "type": "Offre d'emploi",
        "title": offer.titre,
        "description": offer.description[:140],
        "price": offer.salaire_display,
        "image": _image_url(offer, "logo"),
        "url": _safe_url(offer),
        "contact_url": offer.whatsapp_url,
        "meta": getattr(offer.ville, "nom", ""),
    }


def _items_artisan(artisan, limit):
    realisations = artisan.realisations.all()[:limit]
    items = [
        {
            "type": "Realisation",
            "title": realisation.titre,
            "description": realisation.description or artisan.description[:140],
            "price": "Devis sur demande",
            "image": _image_url(realisation, "image"),
            "url": _safe_url(artisan),
            "contact_url": artisan.whatsapp_url,
            "meta": getattr(artisan.ville, "nom", ""),
        }
        for realisation in realisations
    ]
    if items:
        return items
    metiers = ", ".join(artisan.metiers.values_list("nom", flat=True)[:3])
    return [
        {
            "type": "Service artisan",
            "title": metiers or "Travaux et services",
            "description": artisan.description or "Contactez cet artisan depuis E-Shelle.",
            "price": "Devis sur demande",
            "image": _image_url(artisan, "photo"),
            "url": _safe_url(artisan),
            "contact_url": artisan.whatsapp_url,
            "meta": getattr(artisan.ville, "nom", ""),
        }
    ]


def _item_direct_listing(obj, item_type, default_meta):
    title = _read_attr(obj, "titre", "nom", "name", default=str(obj))
    description = _read_attr(obj, "description", default="") or ""
    price = _read_attr(obj, "prix_formate", default="")
    contact = ""
    if hasattr(obj, "get_whatsapp_url"):
        try:
            contact = obj.get_whatsapp_url()
        except Exception:
            contact = ""
    return {
        "type": item_type,
        "title": title,
        "description": description[:140],
        "price": price or "Prix a discuter",
        "image": _primary_photo_url(obj),
        "url": _safe_url(obj),
        "contact_url": contact,
        "meta": _read_attr(obj, "ville", default=default_meta),
    }


def _item_tibo_product(product):
    image_obj = product.primary_image() if hasattr(product, "primary_image") else None
    return {
        "type": "Produit",
        "title": product.title,
        "description": getattr(product, "short_description", "") or getattr(product, "description", "")[:140],
        "price": _money(product.price),
        "image": image_obj.url if image_obj else "",
        "url": _safe_url(product),
        "contact_url": "",
        "meta": getattr(getattr(product, "category", None), "name", "Boutique"),
    }


def _safe_url(obj):
    if hasattr(obj, "get_absolute_url"):
        try:
            return obj.get_absolute_url()
        except Exception:
            return ""
    return ""


def _image_url(obj, field_name):
    image = getattr(obj, field_name, None) if obj else None
    if not image:
        return ""
    try:
        return image.url
    except Exception:
        return ""


def _primary_photo_url(obj):
    photo = getattr(obj, "photo_principale", None)
    if callable(photo):
        try:
            photo = photo()
        except Exception:
            photo = None
    if photo:
        return _image_url(photo, "image")
    return ""


def _money(value, currency="XAF", suffix=""):
    if value in (None, ""):
        return "Prix a discuter"
    try:
        amount = f"{float(value):,.0f}".replace(",", " ")
    except Exception:
        amount = str(value)
    return f"{amount} {currency}{suffix}".strip()


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
