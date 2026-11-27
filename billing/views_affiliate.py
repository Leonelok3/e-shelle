from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .affiliates import attach_referral_if_needed, get_affiliate_by_code
from .models import AffiliateProfile


def ref_redirect(request, ref_code: str):
    """
    /billing/ref/<ref_code>/
    Enregistre le ref_code dans la session puis redirige vers pricing (ou next).
    """
    ref_code = (ref_code or "").strip().upper()
    try:
        affiliate = AffiliateProfile.objects.select_related("user").get(
            ref_code=ref_code,
            is_enabled=True, user__is_active=True,
        )
    except AffiliateProfile.DoesNotExist:
        messages.error(request, "Code de parrainage invalide.")
        return redirect("billing:pricing")

    # On stocke en session (et timestamp)
    AffiliateProfile.objects.filter(pk=affiliate.pk).update(click_count=F("click_count") + 1)
    request.session["ref_code"] = affiliate.ref_code
    request.session["ref_set_at"] = timezone.now().isoformat()
    request.session.modified = True

    nxt = request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(nxt)

    messages.success(request, "✅ Code parrain enregistré.")
    return redirect("business:partner")


@login_required
def affiliate_dashboard(request):
    profile, _ = AffiliateProfile.objects.get_or_create(user=request.user)
    link = request.build_absolute_uri(
        reverse("billing:ref_redirect", kwargs={"ref_code": profile.ref_code})
    )
    messages.success(request, f"Votre lien de parrainage est prêt : {link}")
    return redirect("business:partner_dashboard")


def bind_referral_if_any(request, user):
    ref_code = request.session.get("ref_code") or request.COOKIES.get("ref")
    if not ref_code:
        return None

    return attach_referral_if_needed(user, get_affiliate_by_code(ref_code), source="signup")


def commission_base_from_transaction(tx):
    if tx.amount and Decimal(tx.amount) > 0:
        return Decimal(tx.amount)
    try:
        return Decimal(str((tx.metadata or {}).get("commission_base", "0")))
    except Exception:
        return Decimal("0")
