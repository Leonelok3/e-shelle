# billing/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

# Fonction pour la valeur par défaut de expiration_date
def default_expiration_date():
    return timezone.now() + timedelta(days=30)


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=80, unique=True)
    duration_days = models.PositiveIntegerField(default=1)
    price_usd = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.duration_days}j - {self.price_usd}$)"


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} -> {self.plan} ({self.starts_at:%Y-%m-%d} → {self.expires_at:%Y-%m-%d})"


class CreditCode(models.Model):
    code = models.CharField(max_length=64, unique=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="codes")
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="used_codes")
    used_at = models.DateTimeField(null=True, blank=True)
    expiration_date = models.DateTimeField(default=default_expiration_date)  # <-- corrigé

    def is_valid(self):
        return (not self.is_used) and timezone.now() < self.expiration_date

    def use(self, user=None):
        self.is_used = True
        self.used_at = timezone.now()
        if user:
            self.used_by = user
        self.save()

    def __str__(self):
        state = "used" if self.is_used else "free"
        exp = self.expiration_date.strftime("%Y-%m-%d") if self.expiration_date else "∞"
        return f"{self.code} [{state}] -> {self.plan.name} (exp: {exp})"


class Transaction(models.Model):
    TYPE_CHOICES = (
        ("CREDIT", "Crédit / Achat de pass"),
        ("DEBIT", "Débit"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    type = models.CharField(max_length=12, choices=TYPE_CHOICES, default="CREDIT")
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    related_code = models.ForeignKey(CreditCode, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")

    def __str__(self):
        return f"{self.user} {self.type} {self.amount}{self.currency} ({self.created_at:%Y-%m-%d})"
