import logging
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import ProductView
from .services import normalize_phone, send_abandoned_cart_whatsapp

logger = logging.getLogger(__name__)


def _has_paid_order(product_view, now):
    if not product_view.visitor_phone:
        return False
    try:
        order_lines = apps.get_model("boutique", "LigneCommande").objects.filter(
            produit_id=product_view.boutique_product_id,
            commande__created_at__gte=product_view.viewed_at,
            commande__created_at__lte=now,
            commande__statut__in=("payee", "livree"),
        ).select_related("commande")
        wanted_phone = normalize_phone(product_view.visitor_phone)
        return any(normalize_phone(line.commande.telephone) == wanted_phone for line in order_lines.iterator())
    except Exception:
        logger.warning("WhatsApp Commerce: vérification achat impossible (view_id=%s).", product_view.pk, exc_info=True)
        return False


def check_abandoned_carts():
    """Send one opted-in reminder for an unpurchased product view older than 30 minutes."""
    if not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", True):
        return 0

    cutoff = timezone.now() - timedelta(minutes=30)
    now = timezone.now()
    candidates = ProductView.objects.filter(
        viewed_at__lt=cutoff,
        converted=False,
        abandoned_sent=False,
        whatsapp_opt_in=True,
    ).exclude(visitor_phone__isnull=True).exclude(visitor_phone="").order_by("viewed_at")
    sent_count = 0
    for candidate in candidates.iterator():
        try:
            if _has_paid_order(candidate, now):
                ProductView.objects.filter(pk=candidate.pk, converted=False).update(converted=True)
                continue
            with transaction.atomic():
                claimed = ProductView.objects.filter(
                    pk=candidate.pk,
                    converted=False,
                    abandoned_sent=False,
                ).update(abandoned_sent=True)
            if not claimed:
                continue
            if send_abandoned_cart_whatsapp(candidate):
                sent_count += 1
            else:
                ProductView.objects.filter(pk=candidate.pk, converted=False).update(abandoned_sent=False)
        except Exception:
            ProductView.objects.filter(pk=candidate.pk, converted=False).update(abandoned_sent=False)
            logger.warning("WhatsApp Commerce: traitement vue abandonnée échoué (view_id=%s).", candidate.pk, exc_info=True)
    return sent_count


@shared_task
def process_due_business_whatsapp_follow_ups():
    from .automations import cancel_all_scheduled_follow_ups, send_due_template_follow_ups

    if not getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False):
        cancel_all_scheduled_follow_ups("Les relances WhatsApp ont été désactivées côté serveur.")
        return 0

    return send_due_template_follow_ups()
