"""
models_whatsapp_draft.py — immobilier_cameroun
Brouillons d'annonces immobilières capturées depuis les groupes WhatsApp (ex: ViSLE, E-Shelle Immobilier).
Validation humaine en 1 clic avant publication sur e-shelle.com et partage Facebook.
"""
import uuid
from django.db import models
from django.conf import settings
from .models import Bien, TypeBien, TypeTransaction, VILLES_CAMEROUN


class WhatsappImmoDraft(models.Model):
    """
    Brouillon d'annonce immobilière extrait automatiquement ou manuellement
    d'un message de groupe WhatsApp.
    """
    class Status(models.TextChoices):
        PENDING  = "PENDING",  "En attente de validation"
        APPROVED = "APPROVED", "Validé et publié"
        REJECTED = "REJECTED", "Rejeté"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    raw_text = models.TextField("Message WhatsApp brut")
    raw_images_json = models.JSONField("Photos brutes (chemins)", default=list, blank=True)
    source_name = models.CharField("Nom démarcheur / expéditeur", max_length=150, blank=True, default="Démarcheur WhatsApp")
    source_phone = models.CharField("Téléphone WhatsApp démarcheur", max_length=30, blank=True)
    whatsapp_group_name = models.CharField("Groupe WhatsApp source", max_length=150, default="E-Shelle Immobilier")

    # Données extraites par regex / IA
    parsed_titre = models.CharField("Titre suggéré", max_length=200, blank=True)
    parsed_type_bien = models.CharField(
        "Type de bien", max_length=30, choices=TypeBien.choices, default=TypeBien.STUDIO
    )
    parsed_type_transaction = models.CharField(
        "Transaction", max_length=20, choices=TypeTransaction.choices, default=TypeTransaction.LOCATION
    )
    parsed_prix = models.DecimalField("Prix loyer/vente (XAF)", max_digits=14, decimal_places=0, null=True, blank=True)
    parsed_conditions = models.CharField("Conditions (Avance/Caution)", max_length=150, blank=True)
    parsed_ville = models.CharField("Ville", max_length=100, choices=VILLES_CAMEROUN, default="Yaoundé")
    parsed_quartier = models.CharField("Quartier", max_length=150, blank=True)
    parsed_description = models.TextField("Description brute extraite", blank=True)

    # Enrichissement IA & Sélection Photos
    ai_improved_description = models.TextField("Description optimisée IA & SEO", blank=True)
    ai_selected_photos_json = models.JSONField("Photos retenues par l'IA (max 5)", default=list, blank=True)
    ai_quality_score = models.FloatField("Score qualité IA (0-100)", default=0.0)

    # Workflow & Publication
    status = models.CharField(
        "Statut", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_bien = models.ForeignKey(
        "Bien", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="whatsapp_drafts", verbose_name="Bien créé sur E-Shelle"
    )
    facebook_post_id = models.CharField("ID publication Facebook", max_length=100, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="whatsapp_immo_drafts", verbose_name="Importé par"
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        verbose_name = "Brouillon WhatsApp Immo"
        verbose_name_plural = "Brouillons WhatsApp Immo"
        ordering = ["-created_at"]

    def __str__(self):
        prix_str = f" - {int(self.parsed_prix):,} XAF".replace(",", " ") if self.parsed_prix else ""
        return f"[{self.status}] {self.parsed_titre or 'Brouillon'}{prix_str} ({self.source_phone or self.source_name})"

    @property
    def total_images_count(self):
        return len(self.raw_images_json or [])

    @property
    def selected_images_count(self):
        return len(self.ai_selected_photos_json or [])
