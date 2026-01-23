# billing/affiliates.py
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import AffiliateProfile, Referral, Commission, Transaction
from .services import has_active_access


DEFAULT_AFFILIATE_RATE = Decimal("0.50")


def affiliate_is_allowed(user) -> bool:
    """Un affiliate doit avoir un premium actif."""
    return user.is_authenticated and has_active_access(user)


def get_or_create_affiliate_profile(user) -> AffiliateProfile:
    """Crée le profil affilié si autorisé."""
    profile, _ = AffiliateProfile.objects.get_or_create(
        user=user,
        defaults={
            "rate": DEFAULT_AFFILIATE_RATE,
            "is_active": True,
        },
    )

    # Si l'utilisateur n'est plus premium => désactiver l'affiliation
    if not affiliate_is_allowed(user):
        if profile.is_active:
            profile.is_active = False
            profile.save(update_fields=["is_active"])
    else:
        if not profile.is_active:
            profile.is_active = True
            profile.save(update_fields=["is_active"])

    return profile


def get_affiliate_by_code(code: str):
    if not code:
        return None
    code = code.strip().upper()
    return AffiliateProfile.objects.filter(code__iexact=code, is_active=True).select_related("user").first()


def attach_referral_if_needed(referred_user, affiliate_profile, source="link"):
    """
    Attache un referral (1 fois).
    - Ne crée pas si déjà existant
    - Empêche auto-parrainage
    """
    if not referred_user.is_authenticated or not affiliate_profile:
        return None
    if affiliate_profile.user_id == referred_user.id:
        return None

    ref = Referral.objects.filter(referred_user=referred_user).select_related("affiliate").first()
    if ref:
        return ref

    return Referral.objects.create(
        affiliate=affiliate_profile,
        referred_user=referred_user,
        source=source,
    )


def _commission_base_for_transaction(tx: Transaction) -> Decimal:
    """
    Commission base:
    - paiement: base = tx.amount
    - code redeem: tx.amount peut être 0 => base = plan.price_usd (ou metadata['commission_base'])
    """
    if tx.amount and tx.amount > 0:
        return Decimal(tx.amount)

    # Si redeem code: base = prix plan
    if tx.plan_id:
        return Decimal(tx.plan.price_usd)

    # fallback metadata
    base = (tx.metadata or {}).get("commission_base")
    if base:
        try:
            return Decimal(str(base))
        except Exception:
            pass

    return Decimal("0.00")


@db_transaction.atomic
def create_commission_for_transaction(tx: Transaction) -> Commission | None:
    """
    Crée la commission (si applicable) pour une transaction COMPLETED.
    Idempotent: si commission déjà existante => retourne.
    """
    if tx.status != "COMPLETED" or not tx.user_id:
        return None

    # Déjà créée ?
    existing = Commission.objects.filter(transaction=tx).first()
    if existing:
        return existing

    referral = Referral.objects.filter(referred_user_id=tx.user_id).select_related("affiliate", "affiliate__user").first()
    if not referral:
        return None

    affiliate = referral.affiliate
    if not affiliate or not affiliate.is_active:
        return None

    # Affiliate doit être premium actif
    if not affiliate_is_allowed(affiliate.user):
        # Désactive le profil (optionnel mais pratique)
        AffiliateProfile.objects.filter(id=affiliate.id).update(is_active=False)
        return None

    rate = affiliate.rate if affiliate.rate is not None else DEFAULT_AFFILIATE_RATE
    base = _commission_base_for_transaction(tx)
    if base <= 0:
        return None

    amount = (base * Decimal(rate)).quantize(Decimal("0.01"))

    return Commission.objects.create(
        affiliate=affiliate,
        transaction=tx,
        amount=amount,
        currency=tx.currency or "USD",
        rate=rate,
        status="PENDING",
        created_at=timezone.now(),
    )
