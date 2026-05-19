from django.conf import settings
from django.db import models


class DeliveryRequest(models.Model):
    """Demande de livraison volontairement simple pour la V1."""

    class Status(models.TextChoices):
        NOUVELLE = "NOUVELLE", "Nouvelle"
        CONTACTEE = "CONTACTEE", "Prestataire contacté"
        LIVREE = "LIVREE", "Livrée"
        ANNULEE = "ANNULEE", "Annulée"

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ville = models.CharField(max_length=80)
    quartier_ramassage = models.CharField(max_length=120)
    quartier_livraison = models.CharField(max_length=120)
    description_colis = models.CharField(max_length=220)
    statut = models.CharField(max_length=20, choices=Status.choices, default=Status.NOUVELLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demande de livraison"
        verbose_name_plural = "Demandes de livraisons"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Livraison - {self.quartier_ramassage} vers {self.quartier_livraison}"
