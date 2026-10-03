import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from artist_hub.conf import hub_settings


class CastingSession(models.Model):
    """
    Session de casting (ex: Douala Fashion Week 2026).
    Paramétrable et indépendante.
    """

    title = models.CharField(
        max_length=200,
        default="Douala Fashion Week 2026",
        verbose_name=_("Titre du casting"),
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name=_("Slug URL"),
    )
    subtitle = models.CharField(
        max_length=255,
        default="Samedi 26 Décembre 2026 — Hôtel Krystal Palace Douala",
        blank=True,
        verbose_name=_("Sous-titre / Date & Lieu"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Présentation de l'événement et du profil recherché"),
    )
    rules = models.TextField(
        blank=True,
        verbose_name=_("Règlement & conditions"),
        default=(
            "1. Le casting est gratuit.\n"
            "2. L’inscription ne garantit pas la sélection finale.\n"
            "3. Les candidats mineurs doivent impérativement fournir l'autorisation d'un tuteur légal.\n"
            "4. Les photos et vidéos fournies doivent être récentes, fidèles et sans filtres déformants."
        ),
    )
    event_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de l'événement"),
    )
    event_location = models.CharField(
        max_length=255,
        default="Hôtel Krystal Palace, Douala",
        verbose_name=_("Lieu de l'événement"),
    )
    fee_cameroon = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Frais Candidats Cameroun (FCFA)"),
    )
    fee_international = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Frais Candidats International (FCFA)"),
    )
    currency = models.CharField(
        max_length=10,
        default="XAF",
        verbose_name=_("Devise"),
    )
    min_height_male = models.PositiveIntegerField(
        default=183,
        verbose_name=_("Taille minimum Hommes (cm)"),
        help_text=_("Affiche officielle : 1m83 minimum"),
    )
    min_height_female = models.PositiveIntegerField(
        default=175,
        verbose_name=_("Taille minimum Femmes (cm)"),
        help_text=_("Affiche officielle : 1m75 minimum"),
    )
    opens_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Date d'ouverture des inscriptions"),
    )
    closes_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de clôture des inscriptions"),
        help_text=_("Date limite : ex. 28 septembre 2026 à 23h59"),
    )
    max_candidates = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Nombre maximum de candidatures (optionnel)"),
    )
    cover_image = models.ImageField(
        upload_to="artist_hub/casting/covers/",
        null=True,
        blank=True,
        verbose_name=_("Affiche / Image de couverture"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Session active"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "artist_hub"
        ordering = ["-created_at"]
        verbose_name = _("Session de Casting")
        verbose_name_plural = _("Sessions de Casting")

    def __str__(self):
        return f"{self.title} ({self.event_location})"

    @property
    def is_open(self):
        """Indique si la session est actuellement ouverte."""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        if self.max_candidates:
            confirmed_count = self.candidates.filter(
                status__in=[
                    CandidateStatus.INSCRIT,
                    CandidateStatus.PRESELECTIONNE,
                    CandidateStatus.RETENU,
                ]
            ).count()
            if confirmed_count >= self.max_candidates:
                return False
        return True


class CandidateStatus(models.TextChoices):
    EN_ATTENTE_PAIEMENT = "EN_ATTENTE_PAIEMENT", _("À confirmer")
    EN_ATTENTE_VALIDATION = "EN_ATTENTE_VALIDATION", _("En attente de validation")
    INSCRIT = "INSCRIT", _("Inscription confirmée")
    PRESELECTIONNE = "PRESELECTIONNE", _("Présélectionné")
    RETENU = "RETENU", _("Retenu")
    REFUSE = "REFUSE", _("Refusé")


class CandidateGender(models.TextChoices):
    FEMME = "F", _("Femme")
    HOMME = "M", _("Homme")


class Candidate(models.Model):
    """
    Candidat au casting pour GROUP OPUS / Fashion Week Douala.
    """

    session = models.ForeignKey(
        CastingSession,
        on_delete=models.PROTECT,
        related_name="candidates",
        verbose_name=_("Session de casting"),
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name=_("Prénom"),
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name=_("Nom"),
    )
    birth_date = models.DateField(
        verbose_name=_("Date de naissance"),
    )
    gender = models.CharField(
        max_length=5,
        choices=CandidateGender.choices,
        verbose_name=_("Sexe"),
    )
    height_cm = models.PositiveIntegerField(
        verbose_name=_("Taille (en cm)"),
        help_text=_("Exemple : 178 pour 1m78"),
    )
    weight_kg = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Poids (en kg)"),
    )
    measurements = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Mensurations"),
        help_text=_("Poitrine - Taille - Hanches (ex: 88-62-92)"),
    )
    city = models.CharField(
        max_length=120,
        verbose_name=_("Ville"),
    )
    country = models.CharField(
        max_length=120,
        default="Cameroun",
        verbose_name=_("Pays de résidence"),
    )
    is_international = models.BooleanField(
        default=False,
        verbose_name=_("Candidature internationale"),
    )
    phone = models.CharField(
        max_length=35,
        db_index=True,
        verbose_name=_("Numéro WhatsApp / Téléphone"),
    )
    email = models.EmailField(
        db_index=True,
        verbose_name=_("Adresse email"),
    )
    experience = models.TextField(
        blank=True,
        verbose_name=_("Expérience / Défilés précédents"),
    )
    social_links = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Réseaux sociaux (Instagram, TikTok)"),
    )
    candidate_number = models.CharField(
        max_length=35,
        unique=True,
        db_index=True,
        verbose_name=_("Numéro de candidature"),
        help_text=_("Format auto : CAST-2026-0001"),
    )
    access_code = models.CharField(
        max_length=25,
        unique=True,
        db_index=True,
        verbose_name=_("Code d'accès candidat"),
        help_text=_("Code unique permettant au candidat de se connecter et suivre sa candidature"),
    )
    status = models.CharField(
        max_length=35,
        choices=CandidateStatus.choices,
        default=CandidateStatus.EN_ATTENTE_PAIEMENT,
        db_index=True,
        verbose_name=_("Statut du candidat"),
    )
    # Relation vers le paiement générique
    payment = models.OneToOneField(
        "artist_hub.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate",
        verbose_name=_("Paiement associé"),
    )
    video_url = models.URLField(
        blank=True,
        verbose_name=_("Lien vidéo de présentation"),
        help_text=_("Vidéo 30 à 60s (Lien YouTube, TikTok, Drive, Instagram...)"),
    )
    video_file = models.FileField(
        upload_to="artist_hub/casting/videos/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("Fichier vidéo téléversé (30-60s)"),
    )
    # Gestion des mineurs
    is_minor = models.BooleanField(
        default=False,
        verbose_name=_("Est mineur (< 18 ans)"),
    )
    guardian_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Nom complet du tuteur légal"),
    )
    guardian_phone = models.CharField(
        max_length=35,
        blank=True,
        verbose_name=_("Téléphone du tuteur légal"),
    )
    parental_consent = models.BooleanField(
        default=False,
        verbose_name=_("Autorisation parentale accordée"),
    )
    # Consentements obligatoires
    gdpr_consent = models.BooleanField(
        default=False,
        verbose_name=_("Consentement traitement données personnelles"),
    )
    selection_disclaimer_accepted = models.BooleanField(
        default=False,
        verbose_name=_("Accord clause : les frais ne garantissent pas la sélection"),
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name=_("Notes internes du jury / staff"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Date de candidature"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Dernière mise à jour"),
    )

    class Meta:
        app_label = "artist_hub"
        ordering = ["-created_at"]
        verbose_name = _("Candidat")
        verbose_name_plural = _("Candidats")
        constraints = [
            models.UniqueConstraint(
                fields=["session", "phone"],
                name="unique_candidate_phone_per_session",
            )
        ]
        indexes = [
            models.Index(fields=["status", "session"]),
            models.Index(fields=["candidate_number"]),
            models.Index(fields=["access_code"]),
        ]

    def __str__(self):
        return f"{self.candidate_number} - {self.first_name} {self.last_name} ({self.get_status_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """Calcule l'âge exact en années."""
        today = datetime.date.today()
        born = self.birth_date
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def check_and_update_minor_status(self):
        """Met à jour le booléen is_minor selon l'âge calculé."""
        self.is_minor = self.age < 18
        return self.is_minor

    @property
    def required_fee(self):
        """Retourne le montant exigé selon Cameroun ou International."""
        if self.is_international or (self.country and self.country.lower() != "cameroun"):
            return self.session.fee_international
        return self.session.fee_cameroon


class PhotoType(models.TextChoices):
    PORTRAIT = "portrait", _("Photo 1 — Portrait / Visage")
    FULL_LENGTH = "full_length", _("Photo 2 — Plein pied")
    PROFILE = "profile", _("Photo profil")
    OTHER = "other", _("Autre photo")


class CandidatePhoto(models.Model):
    """
    Photos du candidat (Portrait, Plein pied...).
    """

    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Candidat"),
    )
    photo_type = models.CharField(
        max_length=25,
        choices=PhotoType.choices,
        default=PhotoType.PORTRAIT,
        verbose_name=_("Type de photo"),
    )
    image = models.ImageField(
        upload_to="artist_hub/casting/photos/%Y/%m/",
        verbose_name=_("Image"),
    )
    order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage"),
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "artist_hub"
        ordering = ["order", "uploaded_at"]
        verbose_name = _("Photo de candidat")
        verbose_name_plural = _("Photos de candidat")

    def __str__(self):
        return f"{self.candidate.candidate_number} - {self.get_photo_type_display()}"
