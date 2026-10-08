import logging
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone

from .models import ProductView

logger = logging.getLogger(__name__)


def _sync_product_after_commit(product_id):
    try:
        product_model = apps.get_model("boutique", "Produit")
        product = product_model.objects.filter(pk=product_id, is_published=True).first()
        if product is None:
            return
        from .services import sync_product_to_whatsapp_catalog

        sync_product_to_whatsapp_catalog(product)
    except Exception:
        logger.warning("WhatsApp Commerce: sync produit impossible (product_id=%s).", product_id, exc_info=True)


def _product_saved(sender, instance, raw=False, **kwargs):
    if raw or not instance.pk or not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", True):
        return
    transaction.on_commit(lambda product_id=instance.pk: _sync_product_after_commit(product_id))


def _order_saved(sender, instance, raw=False, **kwargs):
    if raw or not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", True):
        return
    if instance.statut not in {"payee", "livree"} or not instance.telephone:
        return
    try:
        from .services import normalize_phone

        phone = normalize_phone(instance.telephone)
        if not phone:
            return
        now = timezone.now()
        for product_id in instance.lignes.values_list("produit_id", flat=True).distinct():
            ProductView.objects.filter(
                boutique_product_id=product_id,
                visitor_phone=phone,
                converted=False,
                viewed_at__gte=now - timedelta(days=30),
                viewed_at__lte=instance.created_at,
            ).update(converted=True)
    except Exception:
        logger.warning("WhatsApp Commerce: conversion de commande impossible (order_id=%s).", instance.pk, exc_info=True)


def _business_item_saved(sender, instance, raw=False, **kwargs):
    if raw or not instance.pk or not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", False):
        return
    item_id = instance.pk

    def sync_after_commit():
        try:
            item = sender.objects.filter(pk=item_id).select_related("business").first()
            if item is None:
                return
            from .business_catalog import sync_business_catalog_item

            sync_business_catalog_item(item)
        except Exception:
            logger.exception(
                "WhatsApp Business: sync post-commit impossible (item_id=%s).",
                item_id,
            )

    transaction.on_commit(sync_after_commit)


post_save.connect(
    _product_saved,
    sender="boutique.Produit",
    dispatch_uid="whatsapp_commerce.sync_boutique_product",
)
post_save.connect(
    _order_saved,
    sender="boutique.Commande",
    dispatch_uid="whatsapp_commerce.convert_product_view",
)
post_save.connect(
    _business_item_saved,
    sender="business.BusinessCatalogItem",
    dispatch_uid="whatsapp_commerce.sync_business_catalog_item",
)
