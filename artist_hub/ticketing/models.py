"""
Modèles pour le module de billetterie (Ticketing).
Squelette réservé aux événements futurs (concerts, défilés, soirées VIP).
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class EventTicketCategory(models.Model):
    """Catégorie de billet (Standard, VIP, VVIP, Pass Créateur)."""

    name = models.CharField(max_length=100, verbose_name=_("Nom du pass"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Prix"))
    total_quantity = models.PositiveIntegerField(verbose_name=_("Quantité totale"))
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "artist_hub"
        verbose_name = _("Catégorie de billet")
        verbose_name_plural = _("Catégories de billets")

    def __str__(self):
        return f"{self.name} ({self.price} XAF)"


class TicketPurchase(models.Model):
    """Achat de billet avec génération de QR code unique."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_category = models.ForeignKey(
        EventTicketCategory,
        on_delete=models.PROTECT,
        related_name="purchases",
    )
    buyer_name = models.CharField(max_length=150)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=35)
    qr_code_token = models.CharField(max_length=64, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "artist_hub"
        verbose_name = _("Billet acheté")
        verbose_name_plural = _("Billets achetés")

    def __str__(self):
        return f"Ticket {self.buyer_name} - {self.ticket_category.name}"
