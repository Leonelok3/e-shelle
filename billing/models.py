# billing/models.py
from decimal import Decimal, ROUND_HALF_UP
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


def default_expiration_date():
    """Valeur par défaut : expiration dans 30 jours"""
    return timezone.now() + timedelta(days=30)


# =============================================================================
# SYSTÈME D'AFFILIATION / REVENDEURS
# =============================================================================

class Affiliate(models.Model):
    """Revendeurs / Affiliés qui gagnent des commissions"""

    STATUS_CHOICES = (
        ('PENDING', 'En attente'),
        ('ACTIVE', 'Actif'),
        ('SUSPENDED', 'Suspendu'),
        ('BANNED', 'Banni'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='affiliate_profile',
        verbose_name="Utilisateur"
    )
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Code de parrainage",
        help_text="Code unique pour identifier les ventes"
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00'),
        verbose_name="Taux de commission (%)",
        help_text="Pourcentage de commission sur chaque vente (ex: 20.00)"
    )
    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total gagné (USD)"
    )
    total_sales = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de ventes"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut"
    )

    # Informations de paiement
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Méthode de paiement",
        help_text="Ex: Mobile Money, Virement bancaire"
    )
    payment_details = models.TextField(
        blank=True,
        verbose_name="Détails de paiement",
        help_text="Numéro de téléphone Mobile Money, RIB, etc."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Affilié / Revendeur"
        verbose_name_plural = "Affiliés / Revendeurs"

    def __str__(self):
        username = getattr(self.user, 'username', str(self.user))
        return f"{username} ({self.referral_code}) - {self.commission_rate}%"


class Commission(models.Model):
    """Commissions gagnées par les affiliés"""

    STATUS_CHOICES = (
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvée'),
        ('PAID', 'Payée'),
        ('CANCELLED', 'Annulée'),
    )

    affiliate = models.ForeignKey(
        Affiliate,
        on_delete=models.CASCADE,
        related_name='commissions',
        verbose_name="Affilié"
    )
    transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
        related_name='commissions',
        verbose_name="Transaction"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant (USD)",
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Pourcentage appliqué"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Payée le"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Commission"
        verbose_name_plural = "Commissions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.affiliate.referral_code} - ${self.amount} ({self.get_status_display()})"


# =============================================================================
# PLANS ET ABONNEMENTS
# =============================================================================

class SubscriptionPlan(models.Model):
    """Plans d'abonnement disponibles"""

    DURATION_CHOICES = (
        (1, '24 heures'),
        (7, '7 jours'),
        (30, '30 jours'),
        (365, '1 an'),
    )

    name = models.CharField(max_length=100, verbose_name="Nom du plan")
    slug = models.SlugField(max_length=80, unique=True)
    duration_days = models.PositiveIntegerField(
        choices=DURATION_CHOICES,
        default=30,
        verbose_name="Durée (jours)"
    )
    price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Prix USD",
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    price_xaf = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=Decimal('0'),
        verbose_name="Prix FCFA"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_popular = models.BooleanField(default=False, verbose_name="Plan populaire")
    features = models.JSONField(default=list, blank=True, verbose_name="Fonctionnalités")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        ordering = ['order', 'duration_days']
        verbose_name = "Plan d'abonnement"
        verbose_name_plural = "Plans d'abonnement"
        indexes = [
            models.Index(fields=['is_active', 'order']),
        ]

    def save(self, *args, **kwargs):
        # Utiliser un taux de conversion configurable depuis settings, fallback à 600
        conversion_rate = getattr(settings, 'USD_TO_XAF_RATE', Decimal('600'))
        # s'assurer que conversion_rate est Decimal
        if not isinstance(conversion_rate, Decimal):
            conversion_rate = Decimal(str(conversion_rate))
        if (not self.price_xaf) or Decimal(str(self.price_xaf)) == Decimal('0'):
            self.price_xaf = (Decimal(self.price_usd) * conversion_rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - ${self.price_usd}"


class Subscription(models.Model):
    """Abonnements actifs des utilisateurs"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)

    # Référence à l'affilié qui a fait la vente
    referred_by = models.ForeignKey(
        Affiliate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referred_subscriptions',
        verbose_name="Parrainé par"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-starts_at']
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def days_remaining(self):
        if self.is_expired():
            return 0
        delta = self.expires_at - timezone.now()
        return delta.days

    def __str__(self):
        username = getattr(self.user, 'username', str(self.user))
        status = "✓" if not self.is_expired() else "✗"
        return f"{status} {username} - {self.plan.name}"


class CreditCode(models.Model):
    """Codes d'accès prépayés"""

    code = models.CharField(max_length=64, unique=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="codes")
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="used_codes")
    used_at = models.DateTimeField(null=True, blank=True)
    expiration_date = models.DateTimeField(default=default_expiration_date)

    # Référence à l'affilié
    created_by_affiliate = models.ForeignKey(
        Affiliate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_codes',
        verbose_name="Créé par l'affilié"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Code prépayé"
        verbose_name_plural = "Codes prépayés"
        indexes = [
            models.Index(fields=['is_used', 'expiration_date']),
        ]

    def is_valid(self):
        return (not self.is_used) and (timezone.now() < self.expiration_date)

    def use(self, user=None):
        """
        Marquer le code comme utilisé de manière atomique (sélect_for_update pour éviter double utilisation concurrente).
        Lève ValueError si déjà utilisé ou expiré.
        """
        with transaction.atomic():
            cc = CreditCode.objects.select_for_update().get(pk=self.pk)
            if cc.is_used:
                raise ValueError("Code déjà utilisé")
            if timezone.now() >= cc.expiration_date:
                raise ValueError("Code expiré")
            cc.is_used = True
            cc.used_at = timezone.now()
            if user:
                cc.used_by = user
            cc.save()
            return cc

    @classmethod
    def generate_unique(cls, groups=3, group_len=4):
        """
        Génère un code unique de la forme XXXX-XXXX-XXXX ...
        groups: nombre de groupes
        group_len: longueur de chaque groupe
        """
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "-".join(
                ''.join(secrets.choice(alphabet) for _ in range(group_len))
                for _ in range(groups)
            )
            if not cls.objects.filter(code=code).exists():
                return code

    def __str__(self):
        state = "✓ Utilisé" if self.is_used else "○ Disponible"
        return f"{self.code} [{state}] - {self.plan.name}"


class Transaction(models.Model):
    """Transactions de paiement"""

    TYPE_CHOICES = (
        ("CREDIT", "Crédit / Achat"),
        ("DEBIT", "Débit"),
        ("REFUND", "Remboursement"),
    )

    STATUS_CHOICES = (
        ("PENDING", "En attente"),
        ("PROCESSING", "En traitement"),
        ("COMPLETED", "Complété"),
        ("FAILED", "Échoué"),
        ("CANCELLED", "Annulé"),
        ("REFUNDED", "Remboursé"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("MOBILE_MONEY", "Mobile Money"),
        ("CARD", "Carte bancaire"),
        ("CODE", "Code prépayé"),
        ("MANUAL", "Manuel"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    plan = models.ForeignKey(SubscriptionPlan, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=8, default="USD")
    type = models.CharField(max_length=12, choices=TYPE_CHOICES, default="CREDIT")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PENDING")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)

    external_transaction_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    related_code = models.ForeignKey(CreditCode, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    related_subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")

    # Référence à l'affilié
    referred_by = models.ForeignKey(
        Affiliate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referred_transactions',
        verbose_name="Transaction via affilié"
    )

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['external_transaction_id']),
        ]

    def __str__(self):
        username = getattr(self.user, 'username', str(self.user))
        return f"#{self.id} - {username} - ${self.amount}"

    def complete(self):
        """
        Marque la transaction comme COMPLETED et applique les effets liés :
        - création d'un abonnement si self.plan est présent
        - création d'une Commission si référé par un Affiliate
        Tout est fait de manière atomique et idempotente.
        """
        # si déjà complétée, rien à faire (idempotence)
        if self.status == 'COMPLETED':
            return self

        with transaction.atomic():
            tx = Transaction.objects.select_for_update().get(pk=self.pk)
            if tx.status == 'COMPLETED':
                return tx

            # marquer comme complété
            tx.status = 'COMPLETED'
            tx.updated_at = timezone.now()
            tx.save()

            # Créer l'abonnement si applicable
            if tx.plan:
                starts = timezone.now()
                expires = starts + timedelta(days=tx.plan.duration_days)
                sub = Subscription.objects.create(
                    user=tx.user,
                    plan=tx.plan,
                    starts_at=starts,
                    expires_at=expires,
                    is_active=True,
                    referred_by=tx.referred_by if getattr(tx, 'referred_by', None) else None
                )
                tx.related_subscription = sub
                tx.save()

            # Créer la commission pour l'affilié si présent
            if tx.referred_by and tx.amount and Decimal(tx.referred_by.commission_rate) > Decimal('0'):
                percent = Decimal(tx.referred_by.commission_rate)
                commission_amount = (Decimal(tx.amount) * (percent / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                Commission.objects.create(
                    affiliate=tx.referred_by,
                    transaction=tx,
                    amount=commission_amount,
                    percentage=percent,
                    status='PENDING',
                )

            # TODO: notifications (email), logs d'audit, webhooks internes, etc.
            return tx
