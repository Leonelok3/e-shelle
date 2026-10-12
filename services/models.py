"""
services/models.py — Module Création Web & Services E-Shelle
Offres, portfolio, devis, configurateur.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class OffreService(models.Model):
    """Les 4 offres de services (vitrine, e-commerce, appli, agent IA)."""
    titre        = models.CharField(max_length=200)
    slug         = models.SlugField(max_length=220, unique=True, blank=True)
    icone        = models.CharField(max_length=10, default="🌐")
    description  = models.TextField()
    titre_en     = models.CharField(max_length=200, blank=True)
    description_en = models.TextField(blank=True)
    features_en  = models.JSONField(default=list, blank=True)
    prix_base    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                        help_text="Null = sur devis")
    delai_jours  = models.PositiveIntegerField(default=7, help_text="Délai de livraison en jours")
    features     = models.JSONField(default=list, blank=True,
                                     help_text='["Feature 1", "Feature 2", ...]')
    is_active    = models.BooleanField(default=True)
    is_featured  = models.BooleanField(default=False)
    ordre        = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "titre"]
        verbose_name = "Offre de service"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    @property
    def display_title(self):
        from django.utils.translation import get_language
        return (self.titre_en or self.titre) if get_language() == "en" else self.titre

    @property
    def display_description(self):
        from django.utils.translation import get_language
        return (self.description_en or self.description) if get_language() == "en" else self.description

    @property
    def display_features(self):
        from django.utils.translation import get_language
        return (self.features_en or self.features) if get_language() == "en" else self.features

    @property
    def prix_affiche(self):
        return f"{int(self.prix_base):,} FCFA".replace(",", " ") if self.prix_base else "Sur devis"


class CategoriePortfolio(models.Model):
    nom   = models.CharField(max_length=100)
    nom_en = models.CharField(max_length=100, blank=True)
    slug  = models.SlugField(unique=True, blank=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

    @property
    def display_name(self):
        from django.utils.translation import get_language
        return (self.nom_en or self.nom) if get_language() == "en" else self.nom


class ProjetPortfolio(models.Model):
    titre       = models.CharField(max_length=200)
    titre_en    = models.CharField(max_length=200, blank=True)
    slug        = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    description_en = models.TextField(blank=True)
    image       = models.ImageField(upload_to="services/portfolio/")
    categorie   = models.ForeignKey(CategoriePortfolio, on_delete=models.PROTECT,
                                     related_name="projets")
    technologies = models.JSONField(default=list, blank=True,
                                     help_text='["Django", "React", "IA", ...]')
    lien_demo   = models.URLField(blank=True)
    lien_code   = models.URLField(blank=True)
    client      = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    ordre       = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordre", "-created_at"]
        verbose_name = "Projet portfolio"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    @property
    def display_title(self):
        from django.utils.translation import get_language
        return (self.titre_en or self.titre) if get_language() == "en" else self.titre

    @property
    def display_description(self):
        from django.utils.translation import get_language
        return (self.description_en or self.description) if get_language() == "en" else self.description


class Devis(models.Model):
    """Demande de devis via configurateur ou formulaire contact."""
    TYPES_PROJET = [
        ("vitrine",      "Site vitrine"),
        ("ecommerce",    "Site e-commerce"),
        ("webapp",       "Application web"),
        ("mobile",       "Application mobile"),
        ("agent_ia",     "Agent IA personnalisé"),
        ("autre",        "Autre"),
    ]
    STATUTS = [
        ("nouveau",     "Nouveau"),
        ("contacte",    "Contacté"),
        ("en_cours",    "En cours d'analyse"),
        ("envoye",      "Devis envoyé"),
        ("accepte",     "Devis accepté"),
        ("refuse",      "Devis refusé"),
        ("termine",     "Projet terminé"),
    ]
    BUDGETS = [
        ("lt50k",       "< 50 000 FCFA"),
        ("50_100k",     "50 000 – 100 000 FCFA"),
        ("100_200k",    "100 000 – 200 000 FCFA"),
        ("200_500k",    "200 000 – 500 000 FCFA"),
        ("gt500k",      "> 500 000 FCFA"),
        ("nd",          "À discuter"),
    ]

    nom          = models.CharField(max_length=200)
    email        = models.EmailField()
    telephone    = models.CharField(max_length=25, blank=True)
    entreprise   = models.CharField(max_length=200, blank=True)
    type_projet  = models.CharField(max_length=20, choices=TYPES_PROJET)
    budget       = models.CharField(max_length=20, choices=BUDGETS, default="nd")
    delai_souhaite = models.CharField(max_length=100, blank=True)
    description  = models.TextField()
    # Données du configurateur (JSON)
    config_data  = models.JSONField(default=dict, blank=True,
                                     help_text="Données du wizard configurateur")
    montant_estime = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    statut       = models.CharField(max_length=20, choices=STATUTS, default="nouveau")
    note_interne = models.TextField(blank=True)
    # Lié à un utilisateur connecté (optionnel)
    utilisateur  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="devis")
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Devis"
        verbose_name_plural = "Devis"

    def __str__(self):
        return f"{self.nom} — {self.type_projet} ({self.statut})"


class ContactMessage(models.Model):
    """Messages du formulaire de contact."""
    SUJETS = [
        ("devis",       "Demande de devis"),
        ("support",     "Support technique"),
        ("partenariat", "Partenariat"),
        ("facturation", "Facturation"),
        ("autre",       "Autre"),
    ]

    nom        = models.CharField(max_length=200)
    email      = models.EmailField()
    telephone  = models.CharField(max_length=25, blank=True)
    sujet      = models.CharField(max_length=20, choices=SUJETS, default="autre")
    message    = models.TextField()
    lu         = models.BooleanField(default=False)
    repondu    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Message contact"

    def __str__(self):
        return f"{self.nom} — {self.sujet} ({self.created_at.strftime('%d/%m/%Y')})"
