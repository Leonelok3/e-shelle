"""Inventory and fulfillment operations for orders confirmed on WhatsApp."""

import re

from django.core import signing
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem

from .checkout import payment_status, verified_order_payment
from .models import WhatsAppDraftOrder, WhatsAppStockHold

ORDER_REQUEST = re.compile(r"^(suivi|re[cç]u|sav|[eé]change|remboursement)\b[\s:#-]*(.*)$", re.IGNORECASE | re.DOTALL)
ORDER_REFERENCE = re.compile(r"\bCMD-[a-f0-9]{8}\b", re.IGNORECASE)


def orders_for_business(business):
    return WhatsAppDraftOrder.objects.filter(
        business=business, contact__business=business, connection__business=business,
        status=WhatsAppDraftOrder.Status.CONFIRMED, boutique_order__business_profile=business,
        boutique_order__whatsapp_contact_id=F("contact_id"),
    ).select_related("boutique_order", "payment_transaction", "catalog_item", "contact")


def paid_orders(rows):
    return rows.filter(payment_transaction__commande_id=F("boutique_order__pk")).filter(verified_order_payment())


def receipt_token(draft):
    return signing.dumps({"business": draft.business_id, "draft": draft.pk, "reference": draft.boutique_order.reference}, salt="whatsapp-order-receipt")


def status_text(draft):
    order = draft.boutique_order
    stage = draft.get_fulfillment_stage_display() if draft.fulfillment_stage and order.statut in {"en_attente", "payee"} else order.get_statut_display()
    if order.statut == "en_attente" and not draft.fulfillment_stage and paid_orders(WhatsAppDraftOrder.objects.filter(pk=draft.pk)).exists():
        stage = "À préparer"
    note = f"\n{draft.delivery_note}" if draft.delivery_note and order.statut not in {"annulee", "remboursee"} else ""
    return f"Commande {order.reference} · {stage}\n{payment_status(getattr(draft, 'payment_transaction', None))}{note}"


def customer_order_reply(contact, body, job):
    request = ORDER_REQUEST.fullmatch(body.strip())
    if not request:
        return None
    action, rest = request[1].casefold(), request[2]
    reference = ORDER_REFERENCE.search(rest)
    orders = orders_for_business(contact.business).filter(contact=contact)
    if reference:
        orders = orders.filter(boutique_order__reference__iexact=reference[0])
    else:
        candidates = list(orders.order_by("-confirmed_at")[:2])
        if len(candidates) != 1:
            return "Indique la référence de ta commande, par exemple SUIVI CMD-XXXXXXXX.", False
        orders = orders.filter(pk=candidates[0].pk)
    draft = orders.first()
    if draft is None:
        return "Cette commande est introuvable dans ta conversation. Vérifie la référence.", False
    if action == "suivi":
        return status_text(draft), False
    if action in {"reçu", "recu"}:
        if paid_orders(orders).exclude(boutique_order__statut__in=["annulee", "remboursee"]).exists():
            path = reverse("whatsapp_commerce:order_receipt", args=[receipt_token(draft)])
            return f"Voici ton reçu de paiement\n{settings.SITE_URL.rstrip('/')}{path}", False
        return "Le reçu sera disponible après vérification du paiement.", False
    job.follow_up_order_id = draft.pk
    job.follow_up_item_id = draft.catalog_item_id
    return f"Ta demande au sujet de la commande {draft.boutique_order.reference} est transmise à l’équipe.", True


def reserve_stock(draft, item):
    """Called with the catalogue row locked and the confirmed order in the same transaction."""
    if item.stock_quantity is not None:
        BusinessCatalogItem.objects.filter(pk=item.pk).update(stock_quantity=F("stock_quantity") - draft.quantity, updated_at=timezone.now())
        WhatsAppStockHold.objects.create(draft=draft, quantity=draft.quantity)


@transaction.atomic
def settle_stock(order):
    if not order.whatsapp_draft_order_id or order.statut not in {"livree", "annulee", "remboursee"}:
        return
    hold = WhatsAppStockHold.objects.select_for_update(of=("self",)).filter(
        draft_id=order.whatsapp_draft_order_id, draft__business_id=order.business_profile_id,
        status=WhatsAppStockHold.Status.HELD,
    ).select_related("draft").first()
    if hold is None:
        return
    if order.statut == "livree":
        hold.status = WhatsAppStockHold.Status.CONSUMED
    else:
        BusinessCatalogItem.objects.filter(
            pk=hold.draft.catalog_item_id, business_id=order.business_profile_id, stock_quantity__isnull=False,
        ).update(stock_quantity=F("stock_quantity") + hold.quantity, updated_at=timezone.now())
        hold.status = WhatsAppStockHold.Status.RELEASED
    hold.save(update_fields=["status", "updated_at"])
