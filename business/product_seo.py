"""Public offer facts shared by search metadata and the merchant's audit."""

import json
import re
import unicodedata
from decimal import Decimal
from urllib.parse import urljoin, urlsplit

from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

from whatsapp_commerce.catalog_messages import PRICE, format_price


def catalogue_price(label):
    clean = unicodedata.normalize("NFKC", label or "").strip()
    if re.fullmatch(r"(?:\d{1,3}(?: \d{3})+|\d{1,10})", clean):
        clean += " XAF"
    match = PRICE.fullmatch(clean)
    if not match:
        return None
    whole = match["amount"] or match["euro"]
    fraction = match["decimal"] or match["euro_decimal"] or ""
    amount = Decimal(whole.replace(" ", "") + fraction.replace(",", "."))
    token = (match["currency"] or "EUR").upper().replace(" ", "")
    currency = {"FCFA": "XAF", "€": "EUR"}.get(token, token)
    if 0 < amount < Decimal("10000000000") and (currency != "XAF" or amount == amount.to_integral_value()):
        return amount, currency
    return None


def offer_path(public_slug, item_id):
    return reverse("whatsapp_commerce:catalogue_offer", args=[public_slug, item_id])


def catalogue_price_label(label, price):
    return format_price(*price) if price else (label or "").strip()


def offer_type(item_type):
    return {"product": "Product", "menu": "MenuItem", "service": "Service", "delivery": "Service"}.get(item_type, "Thing")


def stock_schema(quantity):
    if quantity is None:
        return ""
    return "https://schema.org/InStock" if quantity else "https://schema.org/OutOfStock"


def catalogue_offer_facts(business, item):
    base = settings.SITE_URL.rstrip("/")
    canonical = base + offer_path(business.public_slug, item.pk)
    location = ", ".join(dict.fromkeys(value.strip() for value in (business.district, business.city, business.country) if value.strip()))
    title = item.display_title
    price = catalogue_price(item.display_price_label)
    price_label = catalogue_price_label(item.display_price_label, price)
    description = " ".join(item.display_description.split())
    summary = description or " · ".join(part for part in (title, business.display_name, location, price_label) if part)
    images = [item.image_url] + [photo.image.url for photo in item.images.all() if photo.image]
    images = list(dict.fromkeys(urljoin(base + "/", url) for url in images if url and urlsplit(url).scheme in {"", "http", "https"}))
    seller = {"@type": "Organization", "name": business.display_name, "url": base + business.get_absolute_url()}
    if location:
        seller["address"] = {"@type": "PostalAddress", **{
            name: value for name, value in {"addressLocality": business.city, "addressCountry": business.country}.items() if value
        }}
    schema = {"@context": "https://schema.org", "@type": offer_type(item.item_type), "name": title, "url": canonical}
    if description:
        schema["description"] = description
    if images:
        schema["image"] = images
    if item.sku and schema["@type"] == "Product":
        schema["sku"] = item.sku
    if item.category and schema["@type"] in {"Product", "Service"}:
        schema["category"] = item.category
    if schema["@type"] == "Service":
        schema["provider"] = seller
    if price and schema["@type"] != "Thing":
        amount, currency = price
        offer = {"@type": "Offer", "url": canonical, "price": format(amount, "f"), "priceCurrency": currency, "seller": seller}
        availability = stock_schema(item.stock_quantity) if item.item_type == "product" else ""
        if availability:
            offer["availability"] = availability
        schema["offers"] = offer
    return {
        "canonical": canonical, "location": location, "summary": summary, "price_label": price_label,
        "images": images, "title": " · ".join(dict.fromkeys(part for part in (title, business.display_name, business.city) if part)),
        "schema": mark_safe(json.dumps(schema).translate(str.maketrans({"<": "\\u003C", ">": "\\u003E", "&": "\\u0026"}))),
    }


def catalogue_issues(business, item):
    issues = []
    if not business.is_published or not item.is_active:
        issues.append("Publie la fiche et rends l’article visible pour qu’il puisse être découvert.")
    if len(item.display_description.strip().split()) < 12:
        issues.append("Ajoute une description précise avec les caractéristiques que tu peux confirmer.")
    if not item.image_url and not item.images.exists():
        issues.append("Ajoute une photo représentative de l’offre.")
    if not catalogue_price(item.display_price_label):
        issues.append("Indique un prix exact et sa devise si le tarif est connu, par exemple 4 500 XAF.")
    if item.item_type == "product" and item.stock_quantity is None:
        issues.append("Renseigne le stock disponible si tu peux le tenir à jour.")
    if not business.city.strip():
        issues.append("Renseigne la ville sur la fiche du prestataire pour la recherche locale.")
    return issues
