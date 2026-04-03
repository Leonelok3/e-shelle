"""
Modèles d'abonnement : plans, codes d'accès.
"""
import uuid
import hashlib
import random
import string
from django.db import models
from django.conf import settings
from django.utils import timezone


class EduProfile(models.Model):
    """Profil éducatif lié à l'utilisateur principal du projet hôte."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='edu_profile'
    )
    phone_number = models.CharField(max_length=20, unique=True)
    country = models.CharField(max_length=50, default='CM')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil Étudiant'
        verbose_name_plural = 'Profils Étudiants'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.phone_number}"

    def get_active_subscription(self):
        """Retourne l'abonnement actif, ou None."""
        return AccessCode.objects.filter(
            activated_by=self.user,
            status='active',
            expires_at__gt=timezone.now()
        ).select_related('plan').first()

    @property
    def has_active_subscription(self):
        return self.get_active_subscription() is not None


class SubscriptionPlan(models.Model):
    """Forfait d'abonnement (Trimestriel ou Annuel)."""
    PLAN_CHOICES = [
        ('quarterly', 'Trimestriel'),
        ('annual', 'Annuel'),
    ]
    name = models.CharField(max_length=100, verbose_name='Nom du forfait')
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    price_xaf = models.DecimalField(
        max_digits=10, decimal_places=0,
        verbose_name='Prix (FCFA)'
    )
    duration_days = models.IntegerField(verbose_name='Durée (jours)')
    features = models.JSONField(default=list, verbose_name='Fonctionnalités incluses')
    is_active = models.BooleanField(default=True)
    badge_label = models.CharField(max_length=50, blank=True, help_text='Ex: Populaire, Meilleure offre')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Plan d\'abonnement'
        verbose_name_plural = 'Plans d\'abonnement'
        ordering = ['price_xaf']

    def __str__(self):
        return f"{self.name} — {self.price_xaf} FCFA"

    @property
    def price_formatted(self):
        return f"{int(self.price_xaf):,} FCFA".replace(',', ' ')

    @property
    def duration_label(self):
        if self.duration_days <= 92:
            return '3 mois'
        elif self.duration_days <= 185:
            return '6 mois'
        return '12 mois'


class AccessCode(models.Model):
    """
    Code d'accès généré après paiement confirmé.
    UN code = UN seul appareil autorisé (sécurité anti-partage).
    """
    STATUS_CHOICES = [
        ('unused', 'Non utilisé'),
        ('active', 'Actif'),
        ('expired', 'Expiré'),
        ('revoked', 'Révoqué'),
    ]
    # Format : XXXX-XXXX-XXXX-XXXX
    code = models.CharField(max_length=32, unique=True, verbose_name='Code d\'accès')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='access_codes')
    generated_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unused')

    # Relations paiement & utilisateur
    transaction = models.OneToOneField(
        'PaymentTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='access_code'
    )
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='edu_access_codes'
    )

    # Sécurité : usage unique strict
    activation_count = models.IntegerField(default=0)
    max_activations = models.IntegerField(default=1)

    class Meta:
        verbose_name = 'Code d\'accès'
        verbose_name_plural = 'Codes d\'accès'
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.code} [{self.get_status_display()}]"

    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    @property
    def is_usable(self):
        return (
            self.status == 'active' and
            not self.is_expired and
            self.activation_count < self.max_activations
        )

    def mark_expired(self):
        """Passe le statut à expiré si la date est dépassée."""
        if self.is_expired and self.status == 'active':
            self.status = 'expired'
            self.save(update_fields=['status'])
