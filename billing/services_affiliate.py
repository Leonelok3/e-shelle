# billing/services_affiliate.py
from __future__ import annotations

from decimal import Decimal
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import AffiliateProfile, Referral, Commission, Transaction
from .services import has_active_access

COMMISSION_RATE = Decimal("0.50")  # 50%


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


def compute_commission_base_amount(tx: Transaction) -> Decimal:
    """
    Commission sur:
    - paiements => base = tx.amount
    - codes prépayés => base = prix du plan si tx.amount = 0
    """
    if tx.payment_method == "CODE" or tx.related_code_id is not None:
        if tx.plan and (tx.amount is None or Decimal(tx.amount) == Decimal("0.00")):
            return Decimal(tx.plan.price_usd)
    return Decimal(tx.amount or Decimal("0.00"))


def create_commission_for_transaction(tx: Transaction) -> Commission | None:
    """
    Crée une commission si:
    - tx COMPLETED
    - tx.user a un Referral
    - l'affilié est premium (sinon pas d'affiliation possible)
    - commission pas déjà créée (UniqueConstraint)
    """
    if tx.status != "COMPLETED":
        return None

    referral = getattr(tx.user, "referral", None)
    if not referral:
        return None

    affiliate = referral.affiliate
    # le parrain doit être premium pour être parrain
    if not has_active_access(affiliate.user):
        return None

    base = compute_commission_base_amount(tx)
    if base <= 0:
        # pas de commission si base = 0
        return None

    amount = (base * COMMISSION_RATE).quantize(Decimal("0.01"))

    try:
        with transaction.atomic():
            return Commission.objects.create(
                transaction=tx,
                affiliate=affiliate,
                amount=amount,
                currency=tx.currency or "USD",
                rate=COMMISSION_RATE,
                status="PENDING",
            )
    except IntegrityError:
        # déjà créée
        return getattr(tx, "commission", None)
