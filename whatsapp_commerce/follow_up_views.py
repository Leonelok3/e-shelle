from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .checkout import payment_status
from .entitlements import require_whatsapp_entitlement
from .follow_ups import booking_cases, payment_cases, review_cases
from .models import BusinessWhatsAppReplyJob, WhatsAppDraftOrder
from .views import _owned_business

CASE_TYPES = (
    ("paiements", "Paiements"),
    ("rendez-vous", "Rendez-vous"),
    ("conversations", "Conversations"),
)


@login_required
@require_GET
@never_cache
def follow_up_list(request, business_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_use_crm"):
        return redirect("tarifs")
    groups = {
        "paiements": payment_cases(business).select_related(
            "contact", "catalog_item", "boutique_order", "payment_transaction",
        ).order_by("confirmed_at", "pk"),
        "rendez-vous": booking_cases(business).select_related(
            "message__contact", "follow_up_item", "follow_up_property", "follow_up_service", "follow_up_appointment",
        ).order_by("message__created_at", "pk"),
        "conversations": review_cases(business).select_related(
            "message__contact", "follow_up_item", "follow_up_property", "follow_up_order__boutique_order",
        ).order_by("message__created_at", "pk"),
    }
    tabs = [(kind, label, groups[kind].count()) for kind, label in CASE_TYPES]
    first_open = next((kind for kind, _, total in tabs if total), "paiements")
    selected = request.GET.get("type", "")
    if selected not in groups:
        selected = first_open
    page = Paginator(groups[selected], 25).get_page(request.GET.get("page"))
    if selected == "paiements":
        for order in page:
            payment = getattr(order, "payment_transaction", None)
            order.payment_display = payment_status(payment) if payment else "Transaction à vérifier"
    return render(request, "whatsapp_commerce/follow_ups.html", {
        "business": business, "tabs": tabs, "selected": selected, "page": page,
    })


@login_required
@require_POST
def close_follow_up(request, business_id, kind, case_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_use_crm"):
        return redirect("tarifs")
    if kind == "paiements":
        owned = WhatsAppDraftOrder.objects.filter(business=business, contact__business=business, pk=case_id)
        remaining = payment_cases(business)
    elif kind in {"rendez-vous", "conversations"}:
        owned = BusinessWhatsAppReplyJob.objects.filter(
            connection__business=business, message__contact__business=business,
            pk=case_id, activation_code="", message__is_activation_test=False,
        )
        remaining = booking_cases(business) if kind == "rendez-vous" else review_cases(business)
    else:
        raise Http404
    if not owned.exists():
        raise Http404
    remaining.filter(pk=case_id).update(follow_up_closed_at=timezone.now())
    base = reverse("whatsapp_commerce:follow_up_list", args=[business.pk])
    return redirect(f"{base}?type={kind}")
