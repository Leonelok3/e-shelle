"""Public directory shared by the international catalogue and the home page."""
import json
import re
from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.db.models import BooleanField, Case, Exists, F, OuterRef, Prefetch, Q, Value, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.whatsapp import whatsapp_url
from resto.models import ContactLog, Dish, FoodCategory, Restaurant

from .models import BusinessCatalogItem, BusinessLeadEvent, BusinessProfile
from .services import create_tracking_event, record_event_hit

PAGE_SIZE = 12
PREVIEW_SIZE = 3


def public_business_restaurants():
    # Legacy restaurants have their own approval and subscription and are listed directly.
    return (
        BusinessProfile.publicly_visible()
        .filter(module=BusinessProfile.Module.RESTO)
        .exclude(Q(public_slug__isnull=True) | Q(public_slug=""))
        .exclude(content_type__app_label="resto", content_type__model="restaurant")
    )


def _menu_items():
    return BusinessCatalogItem.objects.filter(
        is_active=True,
        item_type__in=[BusinessCatalogItem.ItemType.MENU, BusinessCatalogItem.ItemType.PRODUCT],
    )


def public_whatsapp_number(number, country=""):
    if not re.fullmatch(r"[+0-9\s().-]+", number or ""):
        return ""
    number = re.sub(r"[\s().-]", "", number)
    if number.startswith("00"):
        number = "+" + number[2:]
    if country.strip().casefold() in {"cameroun", "cameroon"}:
        if re.fullmatch(r"6[0-9]{8}", number):
            number = "+237" + number
        elif re.fullmatch(r"2376[0-9]{8}", number):
            number = "+" + number
    return number[1:] if re.fullmatch(r"\+[1-9][0-9]{7,14}", number) else ""


def _select_entries(businesses, restaurants):
    business_ids = businesses.order_by().annotate(
        directory_featured=Case(
            When(boost_expires_at__gt=timezone.now(), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
        directory_kind=Value("business"),
    ).values("directory_featured", "created_at", "directory_kind", "pk")
    legacy_ids = restaurants.order_by().annotate(
        directory_featured=F("is_featured"), directory_kind=Value("resto"),
    ).values("directory_featured", "created_at", "directory_kind", "pk")
    return business_ids.union(legacy_ids, all=True).order_by(
        "-directory_featured", "-created_at", "directory_kind", "-pk",
    )


def _image_url(*images):
    return next((image.url for image in images if image), "")


def _make_cards(entries, businesses, restaurants):
    entries = list(entries)
    business_ids = [entry["pk"] for entry in entries if entry["directory_kind"] == "business"]
    legacy_ids = [entry["pk"] for entry in entries if entry["directory_kind"] == "resto"]
    business_rows = businesses.filter(pk__in=business_ids).prefetch_related(
        Prefetch("catalog_items", _menu_items().order_by("order", "-created_at", "pk")[:3], to_attr="directory_menu"),
    ).in_bulk()
    legacy_rows = restaurants.filter(pk__in=legacy_ids).select_related("city", "neighborhood").prefetch_related(
        "categories",
        Prefetch("dishes", Dish.objects.filter(is_active=True).order_by("order", "name", "pk")[:3], to_attr="directory_menu"),
    ).in_bulk()
    cards = []
    for entry in entries:
        kind, pk = entry["directory_kind"], entry["pk"]
        row = (business_rows if kind == "business" else legacy_rows).get(pk)
        if row is None:
            continue
        if kind == "business":
            card = {
                "name": row.display_name, "city": row.city, "district": row.district,
                "country": row.country, "cuisines": [],
                "menu": [(item.display_title, item.display_price_label) for item in row.directory_menu],
                "image": _image_url(row.promo_image, row.logo, *(item.image for item in row.directory_menu)),
                "url": row.get_absolute_url(),
                "can_contact": bool(public_whatsapp_number(row.whatsapp, row.country)),
            }
        else:
            card = {
                "name": row.name, "city": row.city.name, "district": row.neighborhood.name if row.neighborhood else "",
                "country": "", "cuisines": [category.localized_name for category in row.categories.all()],
                "menu": [(dish.localized_name, dish.formatted_price) for dish in row.directory_menu],
                "image": _image_url(row.cover_image, row.logo, *(dish.image for dish in row.directory_menu)),
                "url": reverse("resto:restaurant_detail", args=[row.slug]),
                "can_contact": bool(public_whatsapp_number(row.whatsapp, "Cameroun")),
            }
        cards.append({**card, "kind": kind, "id": pk, "featured": entry["directory_featured"]})
    return cards


def featured_cards():
    businesses, restaurants = public_business_restaurants(), Restaurant.objects.visible()
    entries = list(_select_entries(businesses, restaurants)[:PREVIEW_SIZE])
    if len(entries) < PREVIEW_SIZE:
        return []
    return _make_cards(entries, businesses, restaurants)


def _facet(businesses, restaurants, business_field, legacy_field):
    def values(queryset, field):
        return (
            queryset.order_by().filter(**{f"{field}__isnull": False}).exclude(**{field: ""})
            .annotate(directory_value=F(field)).values_list("directory_value", flat=True)
        )

    choices = values(businesses, business_field).union(values(restaurants, legacy_field))
    return sorted(choices, key=str.casefold)


def _contact(request):
    kind, pk = request.POST.get("kind"), request.POST.get("restaurant_id", "")
    if not re.fullmatch(r"[1-9][0-9]{0,9}", pk):
        raise Http404
    if kind == "business":
        restaurant = get_object_or_404(public_business_restaurants(), pk=pk)
        number = public_whatsapp_number(restaurant.whatsapp, restaurant.country)
    elif kind == "resto":
        restaurant = get_object_or_404(Restaurant.objects.visible(), pk=pk)
        number = public_whatsapp_number(restaurant.whatsapp, "Cameroun")
    else:
        raise Http404
    if not number:
        raise Http404

    target = whatsapp_url(f"Bonjour, je t’écris depuis E-Shelle au sujet de {restaurant.name}.", number)
    if kind == "business":
        event = create_tracking_event(
            restaurant, BusinessLeadEvent.EventType.WHATSAPP, target, source="restaurant_directory",
        )
        target = record_event_hit(event, request=request)
    else:
        ContactLog.objects.create(restaurant=restaurant, action="whatsapp", session_key=request.session.session_key or "")
    return redirect(target)


@require_http_methods(["GET", "HEAD", "POST"])
def directory(request):
    if request.method == "POST":
        return _contact(request)

    filters = {
        field: request.GET.get(field, "").strip()[:limit]
        for field, limit in (("city", 100), ("district", 120), ("cuisine", 120), ("q", 140))
    }
    city, district, cuisine, search = (filters[field] for field in ("city", "district", "cuisine", "q"))
    businesses, restaurants = public_business_restaurants(), Restaurant.objects.visible()
    cities = _facet(businesses, restaurants, "city", "city__name")
    city_label = next((label for label in cities if label.casefold() == city.casefold()), "")
    if city:
        businesses = businesses.filter(city__iexact=city)
        restaurants = restaurants.filter(city__name__iexact=city)
    districts = _facet(businesses, restaurants, "district", "neighborhood__name")
    if district:
        businesses = businesses.filter(district__iexact=district)
        restaurants = restaurants.filter(neighborhood__name__iexact=district)
    cuisines = FoodCategory.objects.filter(restaurant__in=restaurants).order_by("name").distinct()
    if cuisine:
        businesses = businesses.none()
        restaurants = restaurants.filter(categories__in=FoodCategory.objects.filter(slug=cuisine)).distinct()
    if search:
        matching_items = _menu_items().filter(business=OuterRef("pk")).filter(
            Q(title__icontains=search) | Q(title_en__icontains=search),
        )
        matching_dishes = Dish.objects.filter(restaurant=OuterRef("pk"), is_active=True).filter(
            Q(name__icontains=search) | Q(name_en__icontains=search),
        )
        businesses = businesses.filter(Q(name__icontains=search) | Q(name_en__icontains=search) | Exists(matching_items))
        restaurants = restaurants.filter(Q(name__icontains=search) | Exists(matching_dishes))

    paginator = Paginator(_select_entries(businesses, restaurants), PAGE_SIZE)
    try:
        page = paginator.page(request.GET.get("page", 1))
    except InvalidPage as exc:
        raise Http404 from exc
    cards = _make_cards(page.object_list, businesses, restaurants)

    params = {key: value for key, value in filters.items() if value}
    if city_label:
        params["city"] = city_label
    path = reverse("restaurant_directory")
    origin = settings.SITE_URL.rstrip("/")

    def page_url(number):
        query = urlencode({**params, **({"page": number} if number > 1 else {})})
        return f"{path}?{query}" if query else path

    label = f"Restaurants à {city_label}" if city_label else "Annuaire des restaurants"
    item_list = {
        "@context": "https://schema.org", "@type": "ItemList", "name": label,
        "itemListElement": [
            {"@type": "ListItem", "position": index, "name": card["name"], "url": origin + card["url"]}
            for index, card in enumerate(cards, start=page.start_index())
        ],
    }
    return render(request, "business/restaurant_directory.html", {
        "cards": cards, "page": page, "filters": filters, "cities": cities, "districts": districts, "cuisines": cuisines,
        "title": f"{label} — E-Shelle",
        "description": f"{label} sur E-Shelle. Découvre les établissements inscrits, leurs menus et leur contact WhatsApp.",
        "label": label, "origin": origin,
        "canonical": origin + page_url(page.number),
        "noindex": bool(search or district or cuisine or (city and not city_label)),
        "previous_url": page_url(page.previous_page_number()) if page.has_previous() else "",
        "next_url": page_url(page.next_page_number()) if page.has_next() else "",
        "item_list_json": json.dumps(item_list).replace("<", "\\u003c") if cards else "",
    })
