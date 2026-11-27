# billing/affiliates.py
from decimal import Decimal
from django.db import transaction as db_transaction

from .models import AffiliateProfile, Referral, Commission, Transaction


DEFAULT_AFFILIATE_RATE = Decimal("0.50")
PROVIDER_SUBSCRIPTION_RATE = Decimal("0.30")
SUBSCRIPTION_PRODUCT_TYPES = {
    "business_key_subscription",
    "provider_subscription",
}


def affiliate_is_allowed(user) -> bool:
    """Un partenaire actif peut parrainer et toucher des commissions."""
    return bool(user and user.is_authenticated and user.is_active)


def get_or_create_affiliate_profile(user) -> AffiliateProfile:
    """Crée le profil affilié si autorisé."""
    profile, _ = AffiliateProfile.objects.get_or_create(
        user=user,
        defaults={
            "is_enabled": True,
        },
    )

    return profile


def get_affiliate_by_code(code: str):
    if not code:
        return None
    code = code.strip().upper()
    return AffiliateProfile.objects.filter(ref_code__iexact=code, is_enabled=True, user__is_active=True).select_related("user").first()


def attach_referral_if_needed(referred_user, affiliate_profile, source="link"):
    """
    Attache un referral (1 fois).
    - Ne crée pas si déjà existant
    - Empêche auto-parrainage
    """
    if not referred_user.is_authenticated or not affiliate_profile:
        return None
    if affiliate_profile.user_id == referred_user.id or not affiliate_profile.is_enabled or not affiliate_profile.user.is_active:
        return None

    ref, _ = Referral.objects.get_or_create(
        referred_user=referred_user,
        defaults={"affiliate": affiliate_profile, "attribution_source": source, "ref_code_at_binding": affiliate_profile.ref_code},
    )
    return ref


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


def _is_subscription_transaction(tx: Transaction) -> bool:
    if tx.related_subscription_id:
        return True
    return (tx.metadata or {}).get("product_type") in SUBSCRIPTION_PRODUCT_TYPES


@db_transaction.atomic
def create_commission_for_transaction(tx: Transaction) -> Commission | None:
    """
    Crée une commission pour un abonnement payé par un client parrainé.
    Idempotent: si commission déjà existante => retourne.
    """
    if (
        tx.status != "COMPLETED"
        or not tx.user_id
        or not _is_subscription_transaction(tx)
    ):
        return None

    # Déjà créée ?
    existing = Commission.objects.filter(transaction=tx).first()
    if existing:
        return existing

    referral = Referral.objects.filter(referred_user_id=tx.user_id).select_related("affiliate", "affiliate__user").first()
    if not referral:
        return None

    affiliate = referral.affiliate
    if not affiliate or not affiliate.is_enabled:
        return None

    # Le compte partenaire doit rester actif.
    if not affiliate_is_allowed(affiliate.user):
        AffiliateProfile.objects.filter(id=affiliate.id).update(is_enabled=False)
        return None

    product_type = (tx.metadata or {}).get("product_type")
    if product_type == "provider_subscription":
        rate = PROVIDER_SUBSCRIPTION_RATE
    else:
        rate = getattr(affiliate, "rate", None) or DEFAULT_AFFILIATE_RATE
    base = _commission_base_for_transaction(tx)
    if base <= 0:
        return None

    amount = (base * Decimal(rate)).quantize(Decimal("0.01"))

    commission, _ = Commission.objects.get_or_create(transaction=tx, defaults={
        "affiliate": affiliate, "amount": amount, "currency": tx.currency or "USD", "rate": rate,
        "status": "PENDING", "attribution": {
            "referral_id": referral.pk, "source": referral.attribution_source,
            "code": referral.ref_code_at_binding, "bound_at": referral.created_at.isoformat(),
        },
    })
    return commission
