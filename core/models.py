from django.db import models
from django.conf import settings


class ConsultationRequest(models.Model):
    TYPE_CHOICES = [
        ("visa_etude", "Visa Etudes"),
        ("visa_travail", "Visa Travail"),
        ("residence_permanente", "Résidence Permanente"),
        ("langue", "Préparation Test de Langue (TCF/TEF/DELF/DALF)"),
        ("allemand", "Cours d'Allemand"),
        ("cv", "Création / Optimisation CV"),
        ("profil", "Profil Candidat & Mise en Relation"),
        ("job_search", "Recherche d'Emploi à l'International"),
        ("autre", "Autre / Non listé"),
    ]

    STATUS_CHOICES = [
        ("new", "Nouvelle"),
        ("contacted", "Contacté(e)"),
        ("in_progress", "En cours de traitement"),
        ("completed", "Traité(e)"),
        ("cancelled", "Annulé(e)"),
    ]

    BUDGET_CHOICES = [
        ("less_50", "Moins de 50 €"),
        ("50_100", "50 – 100 €"),
        ("100_200", "100 – 200 €"),
        ("200_plus", "200 € et plus"),
        ("to_discuss", "À discuter"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="consultation_requests",
        verbose_name="Compte utilisateur"
    )

    full_name = models.CharField(max_length=150, verbose_name="Nom complet")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Téléphone / WhatsApp")
    country = models.CharField(max_length=80, blank=True, verbose_name="Pays de résidence actuel")

    consultation_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name="Type de consultation"
    )

    destination_country = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Pays de destination visé"
    )

    message = models.TextField(
        verbose_name="Décrivez votre situation et vos besoins"
    )

    budget = models.CharField(
        max_length=20,
        choices=BUDGET_CHOICES,
        default="to_discuss",
        verbose_name="Budget indicatif"
    )

    preferred_date = models.DateField(
        null=True, blank=True,
        verbose_name="Date de consultation souhaitée"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
        db_index=True,
        verbose_name="Statut"
    )

    admin_notes = models.TextField(
        blank=True,
        verbose_name="Notes internes (admin uniquement)"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de demande")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Demande de consultation"
        verbose_name_plural = "Demandes de consultation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} — {self.get_consultation_type_display()} ({self.get_status_display()})"

    def get_type_icon(self):
        icons = {
            "visa_etude": "🎓",
            "visa_travail": "💼",
            "residence_permanente": "🏠",
            "langue": "🗣️",
            "allemand": "🇩🇪",
            "cv": "📄",
            "profil": "👤",
            "job_search": "🔍",
            "autre": "💬",
        }
        return icons.get(self.consultation_type, "📋")
