"""Tenant-isolated synchronization of BusinessProfile catalog items to Meta."""

import logging
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone

from .entitlements import require_whatsapp_entitlement
from .models import (
    BusinessCatalogWhatsAppSync,
    BusinessWhatsAppConnection,
)
from .onboarding import MetaOnboardingError, _request_meta

logger = logging.getLogger(__name__)


def _public_url(item):
    base_url = getattr(settings, "WHATSAPP_COMMERCE_SITE_URL", "https://e-shelle.com").rstrip("/")
    path = item.business.get_absolute_url()
    return urljoin(f"{base_url}/", f"{path.lstrip('/')}?produit={item.pk}")


def _image_url(item):
    if not item.image:
        return ""
    try:
        url = item.image.url
    except (AttributeError, ValueError):
        return ""
    if url.startswith("https://"):
        return url
    if url.startswith("/"):
        return urljoin(
            getattr(settings, "WHATSAPP_COMMERCE_SITE_URL", "https://e-shelle.com").rstrip("/") + "/",
            url.lstrip("/"),
        )
    return ""


def _price_in_minor_units(price_label):
    match = re.search(r"(?<!\d)\d[\d\s,.]*", str(price_label or ""))
    if not match:
        return None
    value = match.group().strip()
    remaining = f"{price_label or ''}"[:match.start()] + f"{price_label or ''}"[match.end():]
    if re.search(r"\d", remaining):
        return None
    if "." in value and not re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
        return None
    if "," in value and not re.fullmatch(r"\d{1,3}(?:,\d{3})+", value):
        return None
    value = re.sub(r"[\s,.]", "", value)
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value():
        return None
    return int(amount) * 100


def _catalog_for_connection(connection):
    if connection.catalog_id:
        return connection.catalog_id
    result = _request_meta(
        "GET",
        f"{connection.waba_id}/product_catalogs",
        token=connection.get_access_token(),
        params={"fields": "id,name", "limit": 100},
    )
    catalogs = result.get("data", [])
    if not isinstance(catalogs, list) or len(catalogs) != 1:
        raise MetaOnboardingError(
            "Le WABA doit exposer exactement un catalogue Meta pour activer la synchronisation."
        )
    catalog_id = str(catalogs[0].get("id", ""))
    if not re.fullmatch(r"\d{1,64}", catalog_id):
        raise MetaOnboardingError("Meta n’a pas retourné un identifiant de catalogue valide.")
    connection.catalog_id = catalog_id
    connection.save(update_fields=["catalog_id", "updated_at"])
    return catalog_id


def sync_business_catalog_item(item):
    """Upsert one catalog item only into its owner's connected WABA catalog."""
    connection = BusinessWhatsAppConnection.objects.filter(
        business_id=item.business_id,
        status=BusinessWhatsAppConnection.Status.ACTIVE,
    ).first()
    if connection is None:
        return False
    if not require_whatsapp_entitlement(item.business, "can_sync_catalog"):
        return False

    sync, _ = BusinessCatalogWhatsAppSync.objects.get_or_create(
        business_catalog_item=item,
        connection=connection,
        defaults={"retailer_id": f"business-{item.business_id}-item-{item.pk}"},
    )
    try:
        token = connection.get_access_token()
        if not token:
            raise MetaOnboardingError("Le jeton WhatsApp de cette entreprise est indisponible.")
        image_url = _image_url(item)
        price = _price_in_minor_units(item.price_label)
        public_url = _public_url(item)
        if not item.title.strip() or not image_url or price is None:
            raise MetaOnboardingError(
                "Ajoutez un prix numérique en XAF et une image publique HTTPS avant la synchronisation."
            )

        product_data = {
            "name": item.title.strip()[:200],
            "description": item.description.strip()[:5000],
            "availability": "in stock" if item.is_active else "out of stock",
            "condition": "new",
            "price": price,
            "currency": "XAF",
            "image_url": image_url,
            "url": public_url,
            "retailer_id": sync.retailer_id,
        }
        result = _request_meta(
            "POST",
            f"{_catalog_for_connection(connection)}/products",
            token=token,
            form_data={
                **product_data,
                "allow_upsert": "true",
            },
        )
        product_id = str(result.get("id", sync.whatsapp_product_id))
        if not product_id:
            raise MetaOnboardingError("Meta n’a pas confirmé l’identifiant du produit synchronisé.")
        sync.whatsapp_product_id = product_id
        sync.sync_status = BusinessCatalogWhatsAppSync.Status.SYNCED
        sync.last_error = ""
        sync.last_synced_at = timezone.now()
        sync.save(update_fields=[
            "whatsapp_product_id", "sync_status", "last_error", "last_synced_at", "updated_at",
        ])
        return True
    except MetaOnboardingError as exc:
        sync.sync_status = BusinessCatalogWhatsAppSync.Status.FAILED
        sync.last_error = str(exc)[:500]
    except Exception:
        sync.sync_status = BusinessCatalogWhatsAppSync.Status.FAILED
        sync.last_error = "Échec de synchronisation Meta. Réessayez ou contactez le support."
        logger.exception(
            "WhatsApp Business: synchronisation catalogue échouée (item_id=%s, business_id=%s).",
            item.pk,
            item.business_id,
        )
    sync.save(update_fields=["sync_status", "last_error", "updated_at"])
    return False


def sync_business_catalog(business):
    items = business.catalog_items.filter(is_active=True).order_by("pk")
    return {
        "total": items.count(),
        "synced": sum(sync_business_catalog_item(item) for item in items),
    }
