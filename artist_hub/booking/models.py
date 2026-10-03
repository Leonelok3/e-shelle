"""
Modèles pour le module de devis et réservations de prestations (Booking).
Squelette réservé aux demandes de prestations de l'artiste / agence.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class BookingService(models.Model):
    """Types de prestation (Défilé, Showcase, Publicité, Présence VIP...)."""

    title = models.CharField(max_length=150, verbose_name=_("Prestation"))
    description = models.TextField(blank=True)
    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Prix de base indicatif"),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "artist_hub"
        verbose_name = _("Service de prestation")
        verbose_name_plural = _("Services de prestation")

    def __str__(self):
        return self.title


class BookingRequest(models.Model):
    """Demande de devis ou de réservation client."""

    service = models.ForeignKey(
        BookingService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
    )
    client_name = models.CharField(max_length=150)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=35)
    event_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        default="PENDING",
        choices=[
            ("PENDING", _("En attente")),
            ("ACCEPTED", _("Acceptée")),
            ("DECLINED", _("Refusée")),
            ("PAID", _("Acompte réglé")),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "artist_hub"
        verbose_name = _("Demande de réservation")
        verbose_name_plural = _("Demandes de réservation")

    def __str__(self):
        return f"Booking {self.client_name} ({self.created_at.strftime('%d/%m/%Y')})"
