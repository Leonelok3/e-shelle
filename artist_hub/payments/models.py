import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


from .storage import private_proof_storage


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", _("En attente")
    SUCCESS = "SUCCESS", _("Succès")
    FAILED = "FAILED", _("Échec")
    CANCELLED = "CANCELLED", _("Annulé")
    EXPIRED = "EXPIRED", _("Expiré")


class PaymentMethod(models.TextChoices):
    MTN_MOMO = "mtn_momo", _("MTN Mobile Money")
    ORANGE_MONEY = "orange_money", _("Orange Money")
    ECOBANK_RIB = "ecobank_rib", _("Virement / Dépôt Ecobank")
    CARD = "card", _("Carte bancaire (Visa / Mastercard)")
    MANUAL = "manual", _("Manuel / Espèces / Autre")


class Payment(models.Model):
    """
    Modèle de paiement centralisé et portable.
    Utilisable par casting, billetterie, devis booking via GenericForeignKey.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Référence unique"),
        help_text=_("Exemple : PAY-20261002-XYZ"),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Montant"),
    )
    currency = models.CharField(
        max_length=10,
        default="XAF",
        verbose_name=_("Devise"),
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
        verbose_name=_("Statut"),
    )
    provider = models.CharField(
        max_length=50,
        default="mock",
        verbose_name=_("Fournisseur de paiement"),
        help_text=_("manual_proof, mock, notchpay, cinetpay"),
    )
    method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MTN_MOMO,
        blank=True,
        verbose_name=_("Méthode de paiement"),
    )
    payer_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Nom du payeur"),
    )
    payer_phone = models.CharField(
        max_length=35,
        blank=True,
        verbose_name=_("Téléphone du payeur"),
    )
    payer_email = models.EmailField(
        blank=True,
        verbose_name=_("Email du payeur"),
    )
    external_reference = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Référence externe opérateur / passerelle"),
        help_text=_("ID de transaction renvoyé par MoMo/OM/passerelle"),
    )
    proof_file = models.FileField(
        storage=private_proof_storage,
        upload_to="artist_hub/proofs/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("Preuve de paiement (capture/reçu)"),
    )
    proof_notes = models.TextField(
        blank=True,
        verbose_name=_("Notes ou détails du versement"),
    )
    # GenericForeignKey pour rattacher à n'importe quel objet métier (Candidature, Billet, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="artist_payments",
    )
    object_id = models.CharField(max_length=64, null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    raw_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Données brutes reçues (webhook/API)"),
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation du paiement"),
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artist_hub_verified_payments",
        verbose_name=_("Validé par (staff)"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Date de création"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Dernière mise à jour"),
    )

    class Meta:
        app_label = "artist_hub"
        ordering = ["-created_at"]
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        indexes = [
            models.Index(fields=["reference", "status"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["payer_phone"]),
        ]

    def __str__(self):
        return f"{self.reference} - {self.amount} {self.currency} ({self.get_status_display()})"

    @property
    def is_successful(self):
        return self.status == PaymentStatus.SUCCESS

    def mark_as_success(self, raw_data=None, verified_by_user=None):
        """Marque le paiement comme validé avec horodatage et idempotence."""
        if self.status == PaymentStatus.SUCCESS:
            return False  # Déjà validé, idempotent
        self.status = PaymentStatus.SUCCESS
        self.verified_at = timezone.now()
        if verified_by_user:
            self.verified_by = verified_by_user
        if raw_data:
            self.raw_payload = raw_data
        self.save(update_fields=["status", "verified_at", "verified_by", "raw_payload", "updated_at"])
        return True
