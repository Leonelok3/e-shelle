from django.conf import settings
from django.db import models


class CourseRequest(models.Model):
    """Demande de délégation du quotidien : achats, retrait simple ou école."""

    class RequestType(models.TextChoices):
        COURSES = "COURSES", "Faire des courses"
        RETRAIT = "RETRAIT", "Récupérer un objet"
        ENFANTS = "ENFANTS", "Récupérer les enfants"

    class Status(models.TextChoices):
        NOUVELLE = "NOUVELLE", "Nouvelle"
        CONTACTEE = "CONTACTEE", "Prestataire contacté"
        TERMINEE = "TERMINEE", "Terminée"
        ANNULEE = "ANNULEE", "Annulée"

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    type_demande = models.CharField(max_length=20, choices=RequestType.choices)
    ville = models.CharField(max_length=80)
    quartier = models.CharField(max_length=120)
    description = models.TextField()
    statut = models.CharField(max_length=20, choices=Status.choices, default=Status.NOUVELLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demande de course"
        verbose_name_plural = "Demandes de courses"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_demande_display()} - {self.quartier}"
