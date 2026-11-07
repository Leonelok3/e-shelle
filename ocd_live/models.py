import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class OpportunityCategory(models.Model):
    name = models.CharField(max_length=120, verbose_name="Nom de la catégorie")
    slug = models.SlugField(max_length=140, unique=True)
    icon = models.CharField(max_length=30, default="💼", help_text="Emoji ou icône représentative")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Catégorie d'opportunité"
        verbose_name_plural = "Catégories d'opportunités"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.icon} {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Opportunity(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Faible (Marché stable & sécurisé)"
        MODERATE = "MODERATE", "Modéré (Rendement attractif)"
        HIGH = "HIGH", "Élevé (Fort potentiel / Venture)"

    class Status(models.TextChoices):
        VERIFIED = "VERIFIED", "Vérifiée & Auditée"
        IN_PROGRESS = "IN_PROGRESS", "Ouverte aux partenaires"
        FUNDED = "FUNDED", "Complétée / Financée"
        ARCHIVED = "ARCHIVED", "Archivée"

    title = models.CharField(max_length=220, verbose_name="Titre de l'opportunité")
    slug = models.SlugField(max_length=250, unique=True)
    category = models.ForeignKey(
        OpportunityCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name="opportunities",
        verbose_name="Catégorie",
    )
    country = models.CharField(max_length=100, default="Cameroun", verbose_name="Pays")
    city = models.CharField(max_length=120, blank=True, verbose_name="Ville / Région")
    summary = models.TextField(
        max_length=500,
        verbose_name="Résumé percutant",
        help_text="Les points clés en 2-3 phrases percutantes",
    )
    full_description = models.TextField(verbose_name="Dossier & Cahier des charges complet")
    
    min_capital_xaf = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("500000.00"),
        verbose_name="Ticket d'entrée / Capital minimum (FCFA)",
    )
    estimated_roi = models.CharField(
        max_length=100,
        default="25% - 40% / an",
        verbose_name="Rentabilité estimée",
    )
    timeframe = models.CharField(
        max_length=100,
        default="6 à 12 mois",
        verbose_name="Horizon d'investissement",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.MODERATE,
        verbose_name="Niveau de risque",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VERIFIED,
        verbose_name="Statut",
    )
    
    pitch_video_url = models.URLField(
        blank=True,
        verbose_name="Lien vidéo de présentation (YouTube / Drive)",
    )
    whatsapp_contact = models.CharField(
        max_length=30,
        default="+237680625082",
        verbose_name="WhatsApp direct du référent terrain",
    )
    cover_image = models.ImageField(
        upload_to="ocd_live/opportunities/",
        blank=True,
        null=True,
        verbose_name="Photo de couverture",
    )
    
    is_featured = models.BooleanField(default=False, verbose_name="Mettre en avant sur la page d'accueil")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de consultations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Opportunité d'affaires"
        verbose_name_plural = "Opportunités d'affaires"
        ordering = ["-is_featured", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.city or self.country})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) + f"-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("ocd_live:opportunity_detail", kwargs={"slug": self.slug})


class LiveSession(models.Model):
    class AccessTier(models.TextChoices):
        FREE = "FREE", "Gratuit (Inscription libre)"
        PASS_REQUIRED = "PASS_REQUIRED", "Pass Membre ou Ticket Unitaire"
        VIP_ONLY = "VIP_ONLY", "Pass VIP Investisseur Uniquement"

    class StreamProvider(models.TextChoices):
        YOUTUBE = "YOUTUBE", "YouTube Live"
        VIMEO = "VIMEO", "Vimeo Live"
        JITSI = "JITSI", "Salon Privé Visioconférence"
        CUSTOM = "CUSTOM", "Flux RTMP / HLS Direct"

    title = models.CharField(max_length=240, verbose_name="Titre de la session Live")
    slug = models.SlugField(max_length=260, unique=True)
    subtitle = models.CharField(max_length=300, blank=True, verbose_name="Sous-titre explicite")
    description = models.TextField(verbose_name="Programme détaillé de l'intervention")
    
    speaker_name = models.CharField(max_length=150, verbose_name="Intervenant / Expert terrain")
    speaker_title = models.CharField(max_length=200, verbose_name="Titre / Spécialité de l'intervenant")
    speaker_avatar = models.ImageField(
        upload_to="ocd_live/speakers/",
        blank=True,
        null=True,
        verbose_name="Photo de l'expert",
    )
    
    scheduled_at = models.DateTimeField(verbose_name="Date et heure de début")
    duration_minutes = models.PositiveIntegerField(default=90, verbose_name="Durée estimée (minutes)")
    
    stream_provider = models.CharField(
        max_length=20,
        choices=StreamProvider.choices,
        default=StreamProvider.YOUTUBE,
        verbose_name="Diffuseur",
    )
    stream_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Lien / ID du flux de diffusion",
        help_text="URL YouTube Live, Vimeo ou salon visio sécurisé",
    )
    
    access_tier = models.CharField(
        max_length=20,
        choices=AccessTier.choices,
        default=AccessTier.PASS_REQUIRED,
        verbose_name="Niveau d'accès",
    )
    ticket_price_xaf = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("2500.00"),
        verbose_name="Prix du ticket unitaire (FCFA)",
        help_text="0 si réservé uniquement aux abonnés ou gratuit",
    )
    
    is_live_now = models.BooleanField(default=False, verbose_name="🔴 En direct maintenant")
    is_completed = models.BooleanField(default=False, verbose_name="Session terminée")
    replay_url = models.URLField(blank=True, verbose_name="Lien du Replay officiel")
    
    banner_image = models.ImageField(
        upload_to="ocd_live/banners/",
        blank=True,
        null=True,
        verbose_name="Bannière d'annonce",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Session Live / Masterclass"
        verbose_name_plural = "Sessions Live / Masterclasses"
        ordering = ["-is_live_now", "scheduled_at"]

    def __str__(self):
        return f"{self.title} — {self.scheduled_at.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) + f"-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return not self.is_completed and not self.is_live_now and self.scheduled_at > timezone.now()

    def get_absolute_url(self):
        return reverse("ocd_live:live_detail", kwargs={"slug": self.slug})


class OCDPackage(models.Model):
    name = models.CharField(max_length=150, verbose_name="Nom du Pass")
    slug = models.SlugField(max_length=170, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Ex: pass_unitaire, pass_mensuel, pass_vip")
    price_xaf = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix (FCFA)")
    duration_days = models.PositiveIntegerField(default=30, verbose_name="Durée de validité (jours)")
    
    can_access_all_lives = models.BooleanField(default=True, verbose_name="Accès illimité à tous les Lives & Replays")
    private_coaching_credits = models.PositiveIntegerField(default=0, verbose_name="Nombre de sessions 1-to-1 incluses")
    full_opportunities_dossier = models.BooleanField(default=True, verbose_name="Accès aux fiches d'audit détaillées des opportunités")
    
    description = models.TextField(verbose_name="Avantages inclus (1 par ligne)")
    is_popular = models.BooleanField(default=False, verbose_name="Badge 'Plus Populaire'")
    is_active = models.BooleanField(default=True, verbose_name="Actif à la vente")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Formule / Pass OCD"
        verbose_name_plural = "Formules & Pass OCD"
        ordering = ["order", "price_xaf"]

    def __str__(self):
        return f"{self.name} — {int(self.price_xaf):,} FCFA".replace(",", " ")

    def feature_list(self):
        return [line.strip() for line in self.description.splitlines() if line.strip()]


class Slot(models.Model):
    """Créneaux réservables pour consultations privées ou sessions VIP."""
    session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="slots",
        verbose_name="Session Live liée (optionnel)",
    )
    title = models.CharField(max_length=180, default="Session d'orientation Opportunité Terrain")
    expert_name = models.CharField(max_length=120, default="Expert Référent OCD Live")
    start_time = models.DateTimeField(verbose_name="Date & Heure de début")
    end_time = models.DateTimeField(verbose_name="Date & Heure de fin")
    capacity = models.PositiveIntegerField(default=1, verbose_name="Capacité maximale (places)")
    booked_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de places réservées")
    price_xaf = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("10000.00"), verbose_name="Prix (FCFA)")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Créneau de réservation"
        verbose_name_plural = "Créneaux de réservation"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.title} : {self.start_time.strftime('%d/%m/%Y %H:%M')} - {self.end_time.strftime('%H:%M')} ({self.available_spots} place(s) dispo)"

    @property
    def available_spots(self):
        return max(0, self.capacity - self.booked_count)

    @property
    def is_full(self):
        return self.booked_count >= self.capacity


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente de paiement"
        CONFIRMED = "CONFIRMED", "Confirmé & Validé"
        CANCELLED = "CANCELLED", "Annulé"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ocd_bookings",
        verbose_name="Utilisateur",
    )
    session = models.ForeignKey(
        LiveSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name="Session Live",
    )
    slot = models.ForeignKey(
        Slot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name="Créneau réservé",
    )
    package = models.ForeignKey(
        OCDPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name="Pass souscrit",
    )
    
    ticket_code = models.CharField(max_length=32, unique=True, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut",
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    whatsapp_number = models.CharField(max_length=30, blank=True, verbose_name="WhatsApp pour notifications")
    
    # Traçabilité paiement centralisé E-Shelle
    transaction_ref = models.CharField(max_length=60, blank=True, verbose_name="Référence Transaction E-Shelle")
    whatsapp_reminder_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Réservation / Ticket OCD Live"
        verbose_name_plural = "Réservations / Tickets OCD Live"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ticket {self.ticket_code} — {self.user.username} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = f"OCD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

