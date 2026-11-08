import uuid
from decimal import Decimal
from datetime import timedelta
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


# ============================================================================
# SYSTÈME OFFICIEL DE RÉSERVATION LIVE OCD (PITCH PRODUITS & SERVICES)
# ============================================================================

class LivePackage(models.Model):
    nom = models.CharField(max_length=150, verbose_name="Nom du package")
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    duree_minutes = models.PositiveIntegerField(verbose_name="Durée en minutes")
    prix_xaf = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix (XAF)")
    description = models.TextField(verbose_name="Description de l'offre")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    est_recommande = models.BooleanField(default=False, verbose_name="Formule Recommandée")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        verbose_name = "Package Live OCD"
        verbose_name_plural = "Packages Live OCD"
        ordering = ["ordre", "prix_xaf"]

    def __str__(self):
        return f"{self.nom} — {self.duree_display} ({int(self.prix_xaf):,} XAF)".replace(",", " ")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom) or f"package-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    @property
    def duree_heures_str(self):
        h = self.duree_minutes // 60
        m = self.duree_minutes % 60
        if m == 0:
            return f"{h}h"
        return f"{h}h{m:02d}"

    @property
    def duree_display(self):
        if self.duree_minutes >= 60:
            h = self.duree_minutes // 60
            m = self.duree_minutes % 60
            if m:
                return f"{h}h{m:02d} ({self.duree_minutes} min)"
            return f"{h}h ({self.duree_minutes} min)"
        return f"{self.duree_minutes} min"

    @property
    def prix_formate(self):
        return f"{int(self.prix_xaf):,} XAF".replace(",", " ")

    @property
    def prix_chiffre_formate(self):
        return f"{int(self.prix_xaf):,}".replace(",", " ")


class LiveSlot(models.Model):
    date = models.DateField(verbose_name="Date du Live")
    heure_debut = models.TimeField(verbose_name="Heure de début")
    heure_fin = models.TimeField(verbose_name="Heure de fin")
    capacite = models.PositiveIntegerField(default=1, verbose_name="Capacité (1 live à la fois)")
    est_disponible = models.BooleanField(default=True, verbose_name="Est disponible")
    est_bloque_admin = models.BooleanField(default=False, verbose_name="Bloqué par l'administrateur")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Créneau Live (LiveSlot)"
        verbose_name_plural = "Créneaux Live (LiveSlots)"
        ordering = ["date", "heure_debut"]
        constraints = [
            models.UniqueConstraint(fields=["date", "heure_debut"], name="unique_liveslot_date_debut"),
        ]

    def __str__(self):
        return f"{self.date.strftime('%d/%m/%Y')} : {self.heure_debut.strftime('%H:%M')} - {self.heure_fin.strftime('%H:%M')}"

    @property
    def est_reservable(self):
        if not self.est_disponible or self.est_bloque_admin:
            return False
        # Empêche 2 réservations confirmées/validées sur le même créneau
        return not self.bookings.filter(
            statut__in=[
                LiveBooking.Statut.VALIDEE_ADMIN,
                LiveBooking.Statut.CONFIRMEE,
                LiveBooking.Statut.EN_ATTENTE_VALIDATION,
            ]
        ).exists()


class LiveBooking(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        EN_ATTENTE_PAIEMENT = "en_attente_paiement", "En attente de paiement"
        EN_ATTENTE_VALIDATION = "en_attente_validation_admin", "En attente de validation admin"
        CONFIRMEE = "confirmee", "Confirmée"
        VALIDEE_ADMIN = "validee_admin", "Validée par l'administrateur"
        REFUSEE = "refusee", "Refusée"
        ANNULEE = "annulee", "Annulée"
        TERMINEE = "terminee", "Terminée"

    class SecteurActivite(models.TextChoices):
        COMMERCE = "Commerce", "Commerce"
        AGRICULTURE = "Agriculture & Élevage", "Agriculture & Élevage"
        IMMOBILIER = "Immobilier & Foncier", "Immobilier & Foncier"
        TRANSPORT = "Transport & Logistique", "Transport & Logistique"
        ENERGIE = "Énergie Solaire & Eau", "Énergie Solaire & Eau"
        TECH = "Tech & IA", "Tech & IA"
        SERVICES = "Services", "Services"
        AUTRE = "Autre", "Autre"

    class ModePaiement(models.TextChoices):
        MTN_MOMO = "MTN MoMo", "MTN MoMo"
        ORANGE_MONEY = "Orange Money", "Orange Money"
        TRANSFERT = "Transfert", "Transfert / Virement"

    code_reservation = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        verbose_name="Code Réservation unique (OCD-2026-XXXX)",
    )

    # Étape 1 - Ton activité & contacts
    nom_complet = models.CharField(max_length=150, verbose_name="Nom complet")
    telephone_whatsapp = models.CharField(max_length=40, verbose_name="Téléphone WhatsApp")
    email = models.EmailField(verbose_name="Email de contact")
    nom_entreprise = models.CharField(max_length=180, verbose_name="Nom de l'entreprise / marque")
    secteur_activite = models.CharField(
        max_length=80,
        choices=SecteurActivite.choices,
        verbose_name="Secteur d'activité",
    )
    titre_du_live = models.CharField(max_length=220, verbose_name="Titre du Live")
    description_activite = models.TextField(verbose_name="Description de ce qui sera présenté")
    produits_services = models.TextField(verbose_name="Liste des produits & services à présenter")
    lien_site_ou_page = models.URLField(blank=True, verbose_name="Lien site web ou page réseaux sociaux")
    lien_whatsapp = models.CharField(max_length=250, blank=True, verbose_name="Lien WhatsApp direct ou catalogue")

    # Étape 2 & 3 - Créneau, Package & Durée
    package = models.ForeignKey(
        LivePackage,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Package choisi",
    )
    slot = models.ForeignKey(
        LiveSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name="Créneau choisi",
    )
    date_choisie = models.DateField(verbose_name="Date du live")
    heure_choisie = models.TimeField(verbose_name="Heure du live")
    duree_minutes = models.PositiveIntegerField(default=60, verbose_name="Durée calculée auto (min)")

    # Étape 4 - Paiement
    prix_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix total (XAF)")
    mode_paiement = models.CharField(
        max_length=50,
        choices=ModePaiement.choices,
        blank=True,
        verbose_name="Mode de paiement",
    )
    reference_paiement = models.CharField(max_length=120, blank=True, verbose_name="Référence transaction / SMS")
    preuve_paiement = models.ImageField(
        upload_to="ocd_live/preuves/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Capture preuve de paiement",
    )

    # Gestion administrateur
    statut = models.CharField(
        max_length=40,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE_PAIEMENT,
        verbose_name="Statut de la réservation",
    )
    message_admin = models.TextField(blank=True, verbose_name="Message / Remarques de l'administrateur")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de demande")
    date_mise_a_jour = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")

    class Meta:
        verbose_name = "Réservation Live OCD"
        verbose_name_plural = "Réservations Live OCD"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.code_reservation} — {self.nom_entreprise or self.nom_complet} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        # 1. Génération du code de réservation unique OCD-YYYY-XXXXX
        if not self.code_reservation:
            year = timezone.now().year
            for _ in range(20):
                suffix = uuid.uuid4().hex[:5].upper()
                candidate = f"OCD-{year}-{suffix}"
                if not LiveBooking.objects.filter(code_reservation=candidate).exists():
                    self.code_reservation = candidate
                    break

        # 2. Synchronisation automatique depuis le package (durée calculée auto & prix)
        if self.package:
            if not self.prix_total or self.prix_total == 0:
                self.prix_total = self.package.prix_xaf
            self.duree_minutes = self.package.duree_minutes

        # 3. Règle métier critique : après envoi preuve / référence, statut -> en_attente_validation_admin
        if self.statut == self.Statut.EN_ATTENTE_PAIEMENT and (self.preuve_paiement or self.reference_paiement):
            self.statut = self.Statut.EN_ATTENTE_VALIDATION

        # 4. Si validée par l'admin, bloquer la disponibilité du créneau
        if self.statut == self.Statut.VALIDEE_ADMIN and self.slot:
            self.slot.est_disponible = False
            self.slot.save(update_fields=["est_disponible"])

        # 5. Si refusée ou annulée, libérer le slot si aucun autre booking validé
        if self.statut in [self.Statut.REFUSEE, self.Statut.ANNULEE] and self.slot:
            has_other_active = self.slot.bookings.exclude(pk=self.pk).filter(
                statut__in=[self.Statut.VALIDEE_ADMIN, self.Statut.CONFIRMEE]
            ).exists()
            if not has_other_active:
                self.slot.est_disponible = True
                self.slot.save(update_fields=["est_disponible"])

        super().save(*args, **kwargs)

    @property
    def heure_arrivee_technique(self):
        """Heure d'arrivée recommandée : 30 minutes avant le début du direct."""
        from datetime import datetime, date
        dummy_date = date(2000, 1, 1)
        full_dt = datetime.combine(dummy_date, self.heure_choisie) - timedelta(minutes=30)
        return full_dt.time()

    @property
    def heure_fin_calculee(self):
        """Heure de fin calculée selon la durée du package."""
        from datetime import datetime, date
        dummy_date = date(2000, 1, 1)
        full_dt = datetime.combine(dummy_date, self.heure_choisie) + timedelta(minutes=self.duree_minutes)
        return full_dt.time()

    @property
    def prix_formate(self):
        return f"{int(self.prix_total):,} XAF".replace(",", " ")

    @property
    def statut_badge_color(self):
        colors = {
            self.Statut.EN_ATTENTE: "#94A3B8",
            self.Statut.EN_ATTENTE_PAIEMENT: "#F59E0B",
            self.Statut.EN_ATTENTE_VALIDATION: "#3B82F6",
            self.Statut.CONFIRMEE: "#10B981",
            self.Statut.VALIDEE_ADMIN: "#10B981",
            self.Statut.REFUSEE: "#EF4444",
            self.Statut.ANNULEE: "#6B7280",
            self.Statut.TERMINEE: "#8B5CF6",
        }
        return colors.get(self.statut, "#94A3B8")


