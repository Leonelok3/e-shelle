from django.conf import settings
from django.db import models


class MotoRequest(models.Model):
    """Demande légère de moto, conservée pour historique sans tracking GPS continu."""

    class Status(models.TextChoices):
        NOUVELLE = "NOUVELLE", "Nouvelle"
        CONTACTEE = "CONTACTEE", "Prestataire contacté"
        TERMINEE = "TERMINEE", "Terminée"
        ANNULEE = "ANNULEE", "Annulée"

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ville = models.CharField(max_length=80)
    quartier_depart = models.CharField(max_length=120)
    destination = models.CharField(max_length=160, blank=True)
    note = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=Status.choices, default=Status.NOUVELLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demande de moto"
        verbose_name_plural = "Demandes de motos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Moto - {self.quartier_depart} vers {self.destination or 'destination à préciser'}"
