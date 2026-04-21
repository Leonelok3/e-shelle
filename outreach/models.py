from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class RecruiterContact(models.Model):
    SECTOR_CHOICES = [
        ("agriculture", "Agriculture / Agroalimentaire"),
        ("construction", "Construction / BTP"),
        ("tech", "Technologie / IT"),
        ("sante", "Santé / Médical"),
        ("logistique", "Transport / Logistique"),
        ("hotellerie", "Hôtellerie / Restauration"),
        ("education", "Éducation / Formation"),
        ("finance", "Finance / Comptabilité"),
        ("industrie", "Industrie / Manufacture"),
        ("commerce", "Commerce / Vente"),
        ("services", "Services aux entreprises"),
        ("autre", "Autre"),
    ]

    COUNTRY_CHOICES = [
        ("CA", "Canada"),
        ("FR", "France"),
        ("DE", "Allemagne"),
        ("BE", "Belgique"),
        ("CH", "Suisse"),
        ("AU", "Australie"),
        ("GB", "Royaume-Uni"),
        ("US", "États-Unis"),
        ("MA", "Maroc"),
        ("SN", "Sénégal"),
        ("CI", "Côte d'Ivoire"),
        ("OTHER", "Autre"),
    ]

    STATUS_CHOICES = [
        ("new", "Nouveau"),
        ("contacted", "Contacté"),
        ("opened", "Email ouvert"),
        ("replied", "A répondu"),
        ("registered", "Inscrit sur la plateforme"),
        ("not_interested", "Pas intéressé"),
        ("bounce", "Bounce / Email invalide"),
    ]

    SOURCE_CHOICES = [
        ("manual", "Ajout manuel"),
        ("csv_import", "Import CSV/Excel"),
        ("ai_search", "Agent IA"),
        ("web", "Recherche web"),
    ]

    # Identité
    company_name = models.CharField("Entreprise", max_length=200)
    contact_name = models.CharField("Nom du contact", max_length=150, blank=True)
    job_title = models.CharField("Poste (ex: DRH, Manager RH)", max_length=120, blank=True)
    email = models.EmailField("Email", unique=True)
    phone = models.CharField("Téléphone", max_length=40, blank=True)
    website = models.URLField("Site web", max_length=300, blank=True)

    # Catégorie
    sector = models.CharField("Secteur", max_length=30, choices=SECTOR_CHOICES, default="autre", db_index=True)
    country = models.CharField("Pays", max_length=10, choices=COUNTRY_CHOICES, default="CA", db_index=True)
    city = models.CharField("Ville", max_length=120, blank=True)

    # Workflow
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default="new", db_index=True)
    source = models.CharField("Source", max_length=20, choices=SOURCE_CHOICES, default="manual")
    tags = models.CharField("Tags", max_length=300, blank=True, help_text="Mots-clés séparés par des virgules")
    notes = models.TextField("Notes internes", blank=True)

    # Suivi
    last_contacted_at = models.DateTimeField("Dernier contact", null=True, blank=True)
    last_replied_at = models.DateTimeField("Dernière réponse", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contact Recruteur"
        verbose_name_plural = "Contacts Recruteurs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} — {self.email}"


class OutreachTemplate(models.Model):
    LANG_CHOICES = [("fr", "Français"), ("en", "Anglais")]

    name = models.CharField("Nom du template", max_length=150)
    language = models.CharField("Langue", max_length=5, choices=LANG_CHOICES, default="fr")
    subject = models.CharField(
        "Objet de l'email", max_length=200,
        help_text="Variables: {company_name}, {contact_name}, {sector_label}, {country_label}"
    )
    body_html = models.TextField(
        "Corps HTML",
        help_text="Variables: {company_name}, {contact_name}, {sector_label}, {country_label}"
    )
    body_text = models.TextField(
        "Corps texte brut",
        help_text="Version texte (fallback). Mêmes variables."
    )
    is_active = models.BooleanField("Actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template Email"
        verbose_name_plural = "Templates Email"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_language_display()}] {self.name}"


class OutreachCampaign(models.Model):
    STATUS_CHOICES = [
        ("draft", "Brouillon"),
        ("sending", "En cours d'envoi"),
        ("sent", "Envoyée"),
        ("paused", "En pause"),
    ]

    name = models.CharField("Nom de la campagne", max_length=200)
    template = models.ForeignKey(
        OutreachTemplate, on_delete=models.PROTECT,
        verbose_name="Template", related_name="campaigns"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Créé par"
    )

    filter_sectors = models.CharField(
        "Secteurs ciblés", max_length=500, blank=True,
        help_text="Vide = tous. Sinon: agriculture,tech,sante"
    )
    filter_countries = models.CharField(
        "Pays ciblés", max_length=200, blank=True,
        help_text="Vide = tous. Sinon: CA,FR,DE"
    )
    filter_status = models.CharField(
        "Statut contacts ciblés", max_length=200, blank=True,
        help_text="Défaut: new,contacted. Vide = tous (hors bounce)."
    )

    total_recipients = models.PositiveIntegerField("Total destinataires", default=0)
    sent_count = models.PositiveIntegerField("Envoyés", default=0)
    opened_count = models.PositiveIntegerField("Ouvertures", default=0)
    replied_count = models.PositiveIntegerField("Réponses", default=0)

    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField("Date d'envoi", null=True, blank=True)

    class Meta:
        verbose_name = "Campagne Outreach"
        verbose_name_plural = "Campagnes Outreach"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def get_filter_sectors_list(self):
        return [s.strip() for s in self.filter_sectors.split(",") if s.strip()] if self.filter_sectors else []

    def get_filter_countries_list(self):
        return [c.strip() for c in self.filter_countries.split(",") if c.strip()] if self.filter_countries else []

    def get_filter_status_list(self):
        if not self.filter_status:
            return ["new", "contacted"]
        return [s.strip() for s in self.filter_status.split(",") if s.strip()]


class OutreachLog(models.Model):
    campaign = models.ForeignKey(OutreachCampaign, on_delete=models.CASCADE, related_name="logs")
    recruiter = models.ForeignKey(RecruiterContact, on_delete=models.SET_NULL, null=True, related_name="outreach_logs")
    tracking_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    opened = models.BooleanField(default=False)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked = models.BooleanField(default=False)
    bounced = models.BooleanField(default=False)
    error = models.CharField(max_length=400, blank=True)

    class Meta:
        verbose_name = "Log Envoi"
        verbose_name_plural = "Logs Envois"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.campaign.name} → {self.recruiter or '?'}"
