# billing/services_affiliate.py
from __future__ import annotations

from django.db import IntegrityError

from .models import AffiliateProfile, Commission, Referral, Transaction
from .services import has_active_access


def ensure_affiliate_profile(user):
    """
    Crée le profil affilié si:
    - user a un abonnement actif (premium)
    """
    if not has_active_access(user):
        return None

    profile = getattr(user, "affiliate_profile", None)
    if profile:
        return profile

    return AffiliateProfile.objects.create(
        user=user,
        ref_code=AffiliateProfile.generate_ref_code(),
        is_enabled=True,
    )


def attach_referral_from_session(request, user):
    """
    À appeler JUSTE après inscription (dans ton app authentification).
    - si session contient ref_code => crée Referral
    """
    ref_code = request.session.get("ref_code")
    if not ref_code:
        return None

    # empêcher auto-parrainage
    try:
        aff = AffiliateProfile.objects.get(ref_code=ref_code, is_enabled=True)
    except AffiliateProfile.DoesNotExist:
        request.session.pop("ref_code", None)
        return None

    if aff.user_id == user.id:
        request.session.pop("ref_code", None)
        return None

    # enregistrer referral (1 seule fois)
    try:
        referral = Referral.objects.create(affiliate=aff, referred_user=user)
    except IntegrityError:
        referral = getattr(user, "referral", None)

    request.session.pop("ref_code", None)
    return referral


def create_commission_for_transaction(tx: Transaction) -> Commission | None:
    """Use the shared subscription-only affiliate commission policy."""
    from .affiliates import create_commission_for_transaction as create_commission

    return create_commission(tx)
