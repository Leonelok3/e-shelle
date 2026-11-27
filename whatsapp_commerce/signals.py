import logging
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.utils import timezone

from .models import BusinessWhatsAppBooking, ProductView, WhatsAppCatalogChange

logger = logging.getLogger(__name__)
CATALOG_FIELDS = {"title": "Nom", "sku": "Référence", "price_label": "Prix", "stock_quantity": "Stock", "image": "Photo", "is_active": "Publication"}


def _catalog_before_save(sender, instance, raw=False, update_fields=None, using=None, **kwargs):
    if not raw and (update_fields is None or CATALOG_FIELDS.keys() & update_fields):
        instance._catalog_previous = sender.objects.using(using).filter(pk=instance.pk).values(*CATALOG_FIELDS).first() if instance.pk else None


def _catalog_after_save(sender, instance, raw=False, update_fields=None, using=None, **kwargs):
    if raw or not hasattr(instance, "_catalog_previous"):
        return
    previous = instance._catalog_previous
    del instance._catalog_previous
    current = {field: getattr(instance, field) for field in CATALOG_FIELDS}
    current["image"] = current["image"].name or ""
    if previous is None:
        changes = {"Création": [None, current["title"]]}
    else:
        previous["image"] = previous["image"] or ""
        changes = {label: [previous[field], current[field]] for field, label in CATALOG_FIELDS.items()
                   if (update_fields is None or field in update_fields) and previous[field] != current[field]}
        if "Photo" in changes:
            changes["Photo"] = [None, "Photo mise à jour"]
    if changes:
        WhatsAppCatalogChange.objects.using(using).create(business_id=instance.business_id, item=instance, title=instance.title, changes=changes)


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


def _record_appointment_completion(sender, instance, raw=False, **kwargs):
    if not raw and instance.status == sender.Status.DONE:
        BusinessWhatsAppBooking.objects.filter(appointment_id=instance.pk, completed_at__isnull=True).update(
            completed_at=timezone.now(),
        )


def _settle_whatsapp_inventory(sender, instance, raw=False, update_fields=None, **kwargs):
    if not raw and (update_fields is None or "statut" in update_fields):
        from .order_operations import settle_stock

        settle_stock(instance)


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
post_save.connect(
    _record_appointment_completion,
    sender="salonhub_bookings.Appointment",
    dispatch_uid="whatsapp_commerce.appointment_completed",
)
post_save.connect(
    _settle_whatsapp_inventory,
    sender="boutique.Commande",
    dispatch_uid="whatsapp_commerce.settle_order_inventory",
)
pre_save.connect(_catalog_before_save, sender="business.BusinessCatalogItem", dispatch_uid="whatsapp_commerce.catalog_before_save")
post_save.connect(_catalog_after_save, sender="business.BusinessCatalogItem", dispatch_uid="whatsapp_commerce.catalog_after_save")
