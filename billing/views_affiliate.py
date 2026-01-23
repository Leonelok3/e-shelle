# billing/views_affiliate.py
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from .models import AffiliateProfile, Referral
from .services import has_active_access


def ref_redirect(request, ref_code: str):
    """
    URL publique: /billing/ref/<ref_code>/
    - Pose le cookie "ref"
    - Redirige vers next ou vers pricing
    """
    next_url = request.GET.get("next") or reverse("billing:pricing")

    response = redirect(next_url)
    response.set_cookie(
        "ref",
        ref_code,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        samesite="Lax",
        secure=False,
    )
    return response


@login_required
def affiliate_dashboard(request):
    """
    Espace parrain. Règle: Pour être parrain => Premium obligatoire.
    """
    if not has_active_access(request.user):
        messages.error(request, "⛔ Pour devenir parrain, vous devez avoir un compte Premium actif.")
        return redirect("billing:pricing")

    profile, _ = AffiliateProfile.objects.get_or_create(user=request.user)

    link = request.build_absolute_uri(
        reverse("billing:ref_redirect", kwargs={"ref_code": profile.ref_code})
    )

    messages.success(request, f"✅ Votre lien de parrainage est prêt : {link}")
    return redirect("billing:wallet")


def bind_referral_if_any(request, user):
    """
    À appeler après signup/login:
    - Lit cookie "ref"
    - Crée Referral si pas encore créé
    """
    ref_code = request.COOKIES.get("ref")
    if not ref_code:
        return

    try:
        affiliate = AffiliateProfile.objects.select_related("user").get(ref_code=ref_code)
    except AffiliateProfile.DoesNotExist:
        return

    # pas d'auto-parrainage
    if affiliate.user_id == user.id:
        return

    # Un user ne peut avoir qu'un parrain
    if Referral.objects.filter(referred_user=user).exists():
        return

    Referral.objects.create(
        affiliate=affiliate,
        referred_user=user,
    )


def commission_base_from_transaction(tx):
    """
    Base commission:
    - Paiement normal => tx.amount
    - Code prépayé => tx.metadata['commission_base'] (si tu la mets)
    """
    if tx.amount and Decimal(tx.amount) > 0:
        return Decimal(tx.amount)

    try:
        return Decimal(str((tx.metadata or {}).get("commission_base", "0")))
    except Exception:
        return Decimal("0")
