from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from boutique.models import Commande
from payments.models import Transaction

from .checkout import payment_status
from .entitlements import require_whatsapp_entitlement
from .inbox import send_business_reply
from .onboarding import MetaOnboardingError
from .order_operations import orders_for_business, paid_orders, receipt_token, status_text
from .views import _owned_business


@login_required
@require_GET
@never_cache
def order_operations(request, business_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_use_crm"):
        return redirect("tarifs")
    rows = orders_for_business(business)
    query = request.GET.get("q", "").strip()[:60]
    if query:
        rows = rows.filter(Q(boutique_order__reference__icontains=query) | Q(catalog_item__title__icontains=query))
    page = Paginator(rows.order_by("-confirmed_at", "-pk"), 25).get_page(request.GET.get("page"))
    orders = list(page)
    paid_ids = set(paid_orders(rows.filter(pk__in=[draft.pk for draft in orders])).values_list("pk", flat=True))
    for draft in orders:
        draft.is_paid = draft.pk in paid_ids
        draft.payment_display = payment_status(getattr(draft, "payment_transaction", None))
        draft.shipping_open = draft.is_paid and draft.boutique_order.statut in {"payee", "en_attente"}
        if draft.is_paid and draft.boutique_order.statut not in {"annulee", "remboursee"}:
            draft.receipt_token = receipt_token(draft)
    return render(request, "whatsapp_commerce/order_operations.html", {
        "business": business, "page": page, "query": query,
        "stock_items": business.catalog_items.filter(is_active=True, stock_quantity__lte=3).order_by("stock_quantity", "title")[:25],
    })


@login_required
@require_POST
def update_order_operations(request, business_id, draft_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_use_crm"):
        return redirect("tarifs")
    rows = orders_for_business(business)
    draft = get_object_or_404(rows, pk=draft_id)
    action = request.POST.get("action")
    if action == "notify":
        try:
            send_business_reply(draft.contact, status_text(draft))
        except MetaOnboardingError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Suivi envoyé sur WhatsApp.")
    else:
        with transaction.atomic():
            order = Commande.objects.select_for_update().get(pk=draft.boutique_order.pk)
            payment = Transaction.objects.select_for_update().filter(whatsapp_draft_order=draft, commande=order).first()
            if action == "cancel" and _can_cancel(order, payment):
                order.statut = "annulee"
                order.save(update_fields=["statut", "updated_at"])
                messages.success(request, "Commande annulée et stock réservé libéré.")
            elif (action in {"preparing", "shipped", "delivered"} and order.statut in {"payee", "en_attente"}
                  and paid_orders(rows.filter(pk=draft.pk)).exists()):
                if action == "delivered":
                    order.statut = "livree"
                    order.save(update_fields=["statut", "updated_at"])
                elif action == "shipped" or draft.fulfillment_stage != "shipped":
                    draft.fulfillment_stage = action
                    draft.delivery_note = request.POST.get("delivery_note", "").strip()[:240]
                    draft.save(update_fields=["fulfillment_stage", "delivery_note"])
                    order.save(update_fields=["updated_at"])
                messages.success(request, "Suivi de livraison mis à jour.")
            else:
                messages.error(request, "Cette action exige un état de commande ou de paiement différent.")
    return redirect("whatsapp_commerce:order_operations", business_id=business.pk)


def _can_cancel(order, payment):
    if order.statut != "en_attente" or not payment or payment.ref_operateur or payment.payment_link and payment.methode == "campay":
        return False
    if payment.methode == "campay":
        return payment.statut == "initie" and not (payment.metadata or {}).get("checkout_requested")
    return payment.statut == "pending_awaiting_manual_validation"


@require_GET
@never_cache
def payment_receipt(request, token):
    try:
        receipt = signing.loads(token, salt="whatsapp-order-receipt", max_age=30 * 86400)
    except signing.BadSignature:
        receipt = {}
    draft = get_object_or_404(paid_orders(orders_for_business(receipt.get("business"))).exclude(
        boutique_order__statut__in=["annulee", "remboursee"],
    ), pk=receipt.get("draft"), boutique_order__reference=receipt.get("reference"))
    response = render(request, "whatsapp_commerce/payment_receipt.html", {"draft": draft, "payment": draft.payment_transaction})
    response["Referrer-Policy"] = "no-referrer"
    response["X-Robots-Tag"] = "noindex"
    return response
