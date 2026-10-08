import logging
import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urljoin

import requests
from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from .models import ProductWhatsAppSync, WhatsAppProviderConfig

logger = logging.getLogger(__name__)


@dataclass
class Provider:
    boutique_id: int
    waba_id: str
    phone_number_id: str
    access_token: str
    catalog_id: str = ""
    display_phone_number: str = ""


def normalize_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    elif len(digits) == 9 and digits.startswith("6"):
        digits = "237" + digits
    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        return ""
    return "+" + digits


def _get_value(source, key, default=""):
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _boutique_id(product):
    value = _get_value(product, "boutique_id", None)
    if value is None:
        value = _get_value(product, "vendeur_id", None)
    if value is None:
        value = os.getenv("WHATSAPP_COMMERCE_BOUTIQUE_ID", "0")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _get_provider(product=None):
    boutique_id = _boutique_id(product) if product is not None else int(os.getenv("WHATSAPP_COMMERCE_BOUTIQUE_ID", "0") or 0)
    config = WhatsAppProviderConfig.objects.filter(boutique_id=boutique_id, is_active=True).first()
    if config:
        token = config.get_access_token() or os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        return Provider(
            boutique_id=boutique_id,
            waba_id=config.waba_id or os.getenv("WABA_ID", ""),
            phone_number_id=config.phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            access_token=token,
            catalog_id=config.catalog_id or os.getenv("WHATSAPP_CATALOG_ID", ""),
            display_phone_number=config.display_phone_number or os.getenv("WHATSAPP_BUSINESS_PHONE", ""),
        )
    return Provider(
        boutique_id=boutique_id,
        waba_id=os.getenv("WABA_ID", ""),
        phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        catalog_id=os.getenv("WHATSAPP_CATALOG_ID", ""),
        display_phone_number=os.getenv("WHATSAPP_BUSINESS_PHONE", ""),
    )


def _graph_request(path, provider, method="GET", payload=None, params=None, json_body=False):
    if not provider.access_token:
        raise ValueError("WHATSAPP_ACCESS_TOKEN absent.")
    version = os.getenv("WHATSAPP_GRAPH_API_VERSION", "v25.0")
    url = f"https://graph.facebook.com/{version}/{path.lstrip('/')}"
    response = requests.request(
        method,
        url,
        headers={"Authorization": f"Bearer {provider.access_token}"},
        json=payload if json_body else None,
        data=payload if payload is not None and not json_body else None,
        params=params,
        timeout=(5, 20),
    )
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code >= 400 or data.get("error"):
        error = data.get("error", {})
        raise RuntimeError(f"Meta HTTP {response.status_code}, code {error.get('code', '?')}: {error.get('message', 'réponse invalide')}")
    return data


def _catalog_id(provider):
    if provider.catalog_id:
        return provider.catalog_id
    data = _graph_request(f"{provider.waba_id}/product_catalogs", provider, params={"fields": "id,name", "limit": 100})
    catalogs = data.get("data", [])
    if len(catalogs) != 1:
        raise ValueError("Configure WHATSAPP_CATALOG_ID : le WABA doit exposer un catalogue Meta unique.")
    return str(catalogs[0].get("id", ""))


def _site_url():
    return os.getenv("WHATSAPP_COMMERCE_SITE_URL", "https://e-shelle.com").rstrip("/")


def _product_url(product):
    slug = _get_value(product, "slug", "")
    if slug:
        try:
            return urljoin(_site_url() + "/", reverse("boutique:detail", kwargs={"slug": slug}).lstrip("/"))
        except Exception:
            pass
    supplied = _get_value(product, "url", "") or _get_value(product, "canonical_url", "")
    return supplied if str(supplied).startswith("https://") else ""


def _product_image_url(product):
    thumbnail = _get_value(product, "thumbnail", None)
    if thumbnail:
        try:
            value = thumbnail.url
        except (AttributeError, ValueError):
            value = str(thumbnail)
        if value:
            return urljoin(_site_url() + "/", value)
    value = _get_value(product, "image_url", "")
    return value if str(value).startswith("https://") else ""


def sync_product_to_whatsapp_catalog(boutique_product):
    """Upsert a published Boutique product in its connected WhatsApp catalog."""
    if not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", True):
        return False
    sync_record = None
    try:
        product_id = int(_get_value(boutique_product, "pk", _get_value(boutique_product, "id", 0)))
        provider = _get_provider(boutique_product)
        if not product_id or not provider.waba_id or not provider.access_token:
            logger.warning("WhatsApp Commerce: configuration ou produit incomplet (product_id=%s).", product_id)
            return False
        sync_record, _ = ProductWhatsAppSync.objects.get_or_create(
            boutique_product_id=product_id,
            waba_id=provider.waba_id,
            defaults={"sync_status": "pending"},
        )
        if _get_value(boutique_product, "is_published", True) is False:
            sync_record.sync_status = "skipped"
            sync_record.save(update_fields=["sync_status"])
            return False

        catalog_id = _catalog_id(provider)
        title = str(_get_value(boutique_product, "titre", _get_value(boutique_product, "title", ""))).strip()
        description = str(_get_value(boutique_product, "description", "")).strip()
        url = _product_url(boutique_product)
        image_url = _product_image_url(boutique_product)
        if not title or not url or not image_url:
            raise ValueError("Le produit doit avoir un titre, une URL publique et une image HTTPS.")
        raw_price = _get_value(boutique_product, "prix", _get_value(boutique_product, "price", "0"))
        price = int(Decimal(str(raw_price)) * 100)
        payload = {
            "retailer_id": str(product_id),
            "name": title[:200],
            "description": description[:5000],
            "availability": "in stock",
            "condition": "new",
            "price": price,
            "currency": "XAF",
            "image_url": image_url,
            "url": url,
            "allow_upsert": "true",
        }
        result = _graph_request(f"{catalog_id}/products", provider, method="POST", payload=payload)
        sync_record.whatsapp_product_id = str(result.get("id", sync_record.whatsapp_product_id))
        sync_record.sync_status = "synced"
        sync_record.last_synced_at = timezone.now()
        sync_record.save(update_fields=["whatsapp_product_id", "sync_status", "last_synced_at"])
        return True
    except Exception:
        if sync_record:
            sync_record.sync_status = "failed"
            sync_record.save(update_fields=["sync_status"])
        logger.warning("WhatsApp Commerce: synchronisation catalogue échouée.", exc_info=True)
        return False


def _load_boutique_product(product_id):
    try:
        product_model = apps.get_model("boutique", "Produit")
        return product_model.objects.filter(pk=product_id, is_published=True).first()
    except Exception:
        logger.warning("WhatsApp Commerce: produit Boutique introuvable (product_id=%s).", product_id, exc_info=True)
        return None


def send_abandoned_cart_whatsapp(product_view):
    """Send an approved WhatsApp template only after explicit visitor consent."""
    if not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", True):
        return False
    try:
        phone = normalize_phone(product_view.visitor_phone)
        if not phone or not product_view.whatsapp_opt_in or product_view.converted or product_view.abandoned_sent:
            return False
        product = _load_boutique_product(product_view.boutique_product_id)
        if not product:
            return False
        provider = _get_provider(product)
        if not provider.phone_number_id or not provider.access_token:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_ACCESS_TOKEN absent.")
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.lstrip("+"),
            "type": "template",
            "template": {
                "name": os.getenv("WHATSAPP_ABANDONED_TEMPLATE", "panier_abandonne"),
                "language": {"code": os.getenv("WHATSAPP_ABANDONED_TEMPLATE_LANGUAGE", "fr")},
                "components": [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": product.titre[:1024]},
                        {"type": "text", "text": _product_url(product)[:1024]},
                    ],
                }],
            },
        }
        data = _graph_request(
            f"{provider.phone_number_id}/messages",
            provider,
            method="POST",
            payload=payload,
            json_body=True,
        )
        return bool(data.get("messages"))
    except Exception:
        logger.warning("WhatsApp Commerce: message de rappel non envoyé.", exc_info=True)
        return False


def get_whatsapp_business_phone(product=None):
    provider = _get_provider(product)
    number = provider.display_phone_number
    if not number and provider.phone_number_id and provider.access_token:
        try:
            data = _graph_request(
                provider.phone_number_id,
                provider,
                params={"fields": "display_phone_number"},
            )
            number = data.get("display_phone_number", "")
        except Exception:
            logger.warning("WhatsApp Commerce: numéro public Meta indisponible.", exc_info=True)
    return normalize_phone(number)


def get_whatsapp_order_url(product, phone=None):
    number = normalize_phone(phone) if phone else get_whatsapp_business_phone(product)
    product_url = _product_url(product)
    if not number or not product_url:
        return ""
    title = str(_get_value(product, "titre", _get_value(product, "title", "ce produit")))
    text = f"Bonjour, je souhaite commander : {title} - {product_url}"
    return f"https://wa.me/{number.lstrip('+')}?text={quote(text)}"


def get_whatsapp_schema_extension(product):
    """Return additive JSON-LD Product properties; callers merge, never replace, their schema."""
    extension = {
        "additionalProperty": [{
            "@type": "PropertyValue",
            "name": "Canal de commande",
            "value": "WhatsApp officiel",
        }],
    }
    target = get_whatsapp_order_url(product)
    if target:
        extension["potentialAction"] = {
            "@type": "OrderAction",
            "name": "Commander via WhatsApp officiel",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": target,
                "inLanguage": "fr",
            },
        }
    return extension
