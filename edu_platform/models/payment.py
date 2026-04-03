"""
Modèle PaymentTransaction : transactions Mobile Money (Orange & MTN).
"""
import uuid
from django.db import models
from django.conf import settings


class PaymentTransaction(models.Model):
    """Transaction de paiement via Mobile Money."""
    PROVIDER_CHOICES = [
        ('orange_money', 'Orange Money'),
        ('mtn_momo', 'MTN MoMo'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('initiated', 'Initiée'),
        ('confirmed', 'Confirmée'),
        ('failed', 'Échouée'),
        ('refunded', 'Remboursée'),
        ('expired', 'Expirée'),
    ]

    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name='ID transaction interne'
    )
    # Référence retournée par l'opérateur (Orange / MTN)
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Référence opérateur'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='edu_transactions',
        verbose_name='Utilisateur'
    )
    plan = models.ForeignKey(
        'edu_platform.SubscriptionPlan',
        on_delete=models.PROTECT,
        verbose_name='Plan choisi'
    )
    provider = models.CharField(
        max_length=30,
        choices=PROVIDER_CHOICES,
        verbose_name='Opérateur'
    )
    phone_number = models.CharField(max_length=20, verbose_name='Numéro Mobile Money')
    amount_xaf = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name='Montant (FCFA)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Statut'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    webhook_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Données webhook brutes'
    )
    # Tentatives pour éviter les doublons
    webhook_received_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Transaction Mobile Money'
        verbose_name_plural = 'Transactions Mobile Money'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.get_provider_display()} | {self.amount_xaf} FCFA"
            f" | {self.get_status_display()} | {self.phone_number}"
        )

    @property
    def amount_formatted(self):
        return f"{int(self.amount_xaf):,} FCFA".replace(',', ' ')

    @property
    def is_confirmed(self):
        return self.status == 'confirmed'
