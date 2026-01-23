# billing/models.py
from __future__ import annotations

import secrets
import string
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models, IntegrityError
from django.db.models import Q
from django.utils import timezone

from django.utils import timezone
from datetime import timedelta

def default_expiration_date():
    # Valeur par défaut utilisée par l'ancienne migration 0001_initial.py
    return timezone.now() + timedelta(days=90)

User = get_user_model()


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True, default="")
    duration_days = models.PositiveIntegerField(default=30)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    price_xaf = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # optionnel (utilisé dans tes templates)
    is_popular = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "duration_days")

    def __str__(self) -> str:
        return self.name

    @property
    def duration(self):
        # compat templates si certains utilisent plan.duration
        return self.duration_days

    def get_duration_display(self):
        d = self.duration_days
        if d == 1:
            return "24 heures"
        if d == 7:
            return "7 jours"
        if d == 30:
            return "30 jours"
        if d == 90:
            return "90 jours"
        if d == 365:
            return "1 an"
        return f"{d} jours"


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.plan} ({self.expires_at})"

    @property
    def days_remaining(self) -> int:
        now = timezone.now()
        if self.expires_at <= now:
            return 0
        delta = self.expires_at - now
        return max(0, int(delta.total_seconds() // 86400))

    @classmethod
    def activate_or_extend(cls, user: User, plan: SubscriptionPlan):
        """
        Stacking:
        - si user a un abonnement actif, on prolonge expires_at
        - sinon on crée un nouvel abonnement
        """
        now = timezone.now()
        active = (
            cls.objects.filter(user=user, expires_at__gt=now, is_active=True)
            .select_related("plan")
            .order_by("-expires_at")
            .first()
        )

        if active:
            active.expires_at = active.expires_at + timedelta(days=plan.duration_days)
            active.plan = plan
            active.save(update_fields=["expires_at", "plan"])
            return active, False

        sub = cls.objects.create(
            user=user,
            plan=plan,
            starts_at=now,
            expires_at=now + timedelta(days=plan.duration_days),
            is_active=True,
        )
        return sub, True


class CreditCode(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="credit_codes")

    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="used_codes")
    used_at = models.DateTimeField(null=True, blank=True)
    used_ip = models.GenericIPAddressField(null=True, blank=True)

    expiration_date = models.DateTimeField(null=True, blank=True)

    # multi-uses optionnel (tu as ajouté max_uses / uses_count)
    max_uses = models.PositiveIntegerField(default=1)
    uses_count = models.PositiveIntegerField(default=0)

    batch_id = models.CharField(max_length=32, blank=True, default="", db_index=True)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_credit_codes",
    )

    class Meta:
        indexes = [
            models.Index(fields=["batch_id"]),
        ]

    def __str__(self) -> str:
        return self.code

    @staticmethod
    def generate_unique(prefix="I97", size=12) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            core = "".join(secrets.choice(alphabet) for _ in range(size))
            code = f"{prefix}-{core[:4]}-{core[4:8]}-{core[8:]}"
            if not CreditCode.objects.filter(code=code).exists():
                return code

    def is_expired(self) -> bool:
        return bool(self.expiration_date and timezone.now() > self.expiration_date)

    def can_use(self) -> bool:
        if self.is_expired():
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        return True

    def use(self, user=None, ip=None):
        """
        Consommation atomique
        - gère expiration
        - gère multi-uses
        """
        if not self.can_use():
            raise ValueError("Code expiré ou déjà consommé.")

        # verrou DB simple via update conditionnel
        updated = CreditCode.objects.filter(
            pk=self.pk,
        ).update(
            uses_count=models.F("uses_count") + 1,
            used_at=timezone.now(),
            used_ip=ip or None,
            used_by=user if user and user.is_authenticated else None,
        )

        if updated != 1:
            raise ValueError("Impossible d'utiliser ce code (conflit).")

        self.refresh_from_db()

        # si atteint max_uses => marque is_used
        if self.max_uses and self.uses_count >= self.max_uses:
            if not self.is_used:
                CreditCode.objects.filter(pk=self.pk).update(is_used=True)
                self.is_used = True


class Transaction(models.Model):
    TYPE_CHOICES = (
        ("CREDIT", "CREDIT"),
        ("DEBIT", "DEBIT"),
    )
    STATUS_CHOICES = (
        ("PENDING", "PENDING"),
        ("COMPLETED", "COMPLETED"),
        ("FAILED", "FAILED"),
        ("CANCELED", "CANCELED"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("CODE", "CODE"),
        ("CARD", "CARD"),
        ("MOBILE_MONEY", "MOBILE_MONEY"),
        ("WALLET_TOPUP", "WALLET_TOPUP"),
        ("OTHER", "OTHER"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    plan = models.ForeignKey(SubscriptionPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="USD")

    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="CREDIT")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    payment_method = models.CharField(max_length=32, choices=PAYMENT_METHOD_CHOICES, default="OTHER")

    description = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)

    related_code = models.ForeignKey(CreditCode, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    related_subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"TX#{self.id} {self.user} {self.amount} {self.currency} {self.status}"


# ==========================
# PARRAINAGE (AFFILIATION)
# ==========================

class AffiliateProfile(models.Model):
    """
    Un parrain = un user premium.
    ref_code est utilisé dans les liens: ?ref=XXXXXX
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="affiliate_profile")
    ref_code = models.CharField(max_length=20, unique=True, db_index=True)
    is_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Affiliate({self.user})"

    @staticmethod
    def generate_ref_code() -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            if not AffiliateProfile.objects.filter(ref_code=code).exists():
                return code


class Referral(models.Model):
    """
    Trace: qui a parrainé qui.
    """
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name="referrals")
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.affiliate.ref_code} -> {self.referred_user}"


class Commission(models.Model):
    """
    Commission sur une transaction COMPLETED.
    - Unique par transaction => évite double paiement commission
    """
    STATUS_CHOICES = (
        ("PENDING", "PENDING"),
        ("PAID", "PAID"),
        ("CANCELED", "CANCELED"),
    )

    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name="commission")
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name="commissions")

    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    currency = models.CharField(max_length=8, default="USD")
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.50"))  # 50%

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transaction"], name="uniq_commission_per_transaction"),
        ]

    def __str__(self) -> str:
        return f"Commission({self.affiliate.ref_code}) {self.amount} {self.currency}"
