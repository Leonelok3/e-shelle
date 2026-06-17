from calendar import monthrange
from datetime import date

from django.db import models


class Prestataire(models.Model):
    """Prestataire ayant enregistre une carte Shelle Premium."""

    nom_complet = models.CharField(max_length=200)
    code_premium = models.CharField(max_length=50, unique=True)
    date_expiration = models.CharField(max_length=5)
    adresse = models.TextField()
    date_inscription = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_inscription"]
        verbose_name = "Prestataire Shelle Premium"
        verbose_name_plural = "Prestataires Shelle Premium"

    def __str__(self):
        return f"{self.nom_complet} - {self.code_premium}"

    def est_actif(self):
        """Retourne True si la date d'expiration MM/AA n'est pas depassee."""

        try:
            mois, annee = self.date_expiration.split("/")
            mois_int = int(mois)
            annee_int = 2000 + int(annee)
            dernier_jour = monthrange(annee_int, mois_int)[1]
            expiration = date(annee_int, mois_int, dernier_jour)
        except (TypeError, ValueError):
            return False
        return expiration >= date.today()

