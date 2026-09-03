"""
dashboard/models.py — Tableau de bord & configuration plateforme E-Shelle
Notifications, paramètres, modules actifs.
"""
from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPES = [
        ("achat",       "Nouvel achat"),
        ("inscription", "Nouvelle inscription"),
        ("message",     "Message reçu"),
        ("badge",       "Badge obtenu"),
        ("devis",       "Nouveau devis"),
        ("paiement",    "Paiement reçu"),
        ("systeme",     "Notification système"),
    ]

    destinataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name="notifications")
    type_notif   = models.CharField(max_length=20, choices=TYPES, default="systeme")
    titre        = models.CharField(max_length=200)
    message      = models.TextField(blank=True)
    url_action   = models.CharField(max_length=500, blank=True)
    lue          = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"

    def __str__(self):
        return f"{self.destinataire.username} — {self.titre}"


class ParametrePlateforme(models.Model):
    """Configuration globale de la plateforme (singleton)."""
    nom_site       = models.CharField(max_length=200, default="E-Shelle")
    slogan         = models.CharField(max_length=300, default="L'expérience à votre service")
    logo           = models.ImageField(upload_to="config/", null=True, blank=True)
    favicon        = models.ImageField(upload_to="config/", null=True, blank=True)
    couleur_primaire = models.CharField(max_length=10, default="#2E7D32")
    couleur_accent  = models.CharField(max_length=10, default="#F57C00")
    email_contact   = models.EmailField(default="contact@e-shelle.com")
    telephone       = models.CharField(max_length=25, default="+237 680 625 082")
    whatsapp        = models.CharField(max_length=25, default="+237680625082")
    adresse         = models.TextField(blank=True)
    # Réseaux sociaux
    lien_facebook   = models.URLField(blank=True)
    lien_linkedin   = models.URLField(blank=True)
    lien_youtube    = models.URLField(blank=True)
    lien_whatsapp   = models.URLField(blank=True)
    # SEO
    meta_description = models.CharField(max_length=300, blank=True)
    og_image         = models.ImageField(upload_to="config/", null=True, blank=True)
    produits_services_hero_image = models.ImageField(
        upload_to="config/heros/",
        null=True,
        blank=True,
        help_text="Visuel affiche dans le hero de la page Produits & Services.",
    )
    # Analytics
    google_analytics_id = models.CharField(max_length=50, blank=True)
    # Paiement
    mtn_api_key     = models.CharField(max_length=200, blank=True)
    airtel_api_key  = models.CharField(max_length=200, blank=True)
    # Modules actifs
    module_formations = models.BooleanField(default=True)
    module_boutique   = models.BooleanField(default=True)
    module_services   = models.BooleanField(default=True)
    module_ai         = models.BooleanField(default=True)
    # Mode maintenance
    maintenance       = models.BooleanField(default=False)
    message_maintenance = models.TextField(blank=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètre plateforme"
        verbose_name_plural = "Paramètres plateforme"

    def __str__(self):
        return f"Config {self.nom_site}"

    @classmethod
    def get_config(cls):
        """Récupère ou crée la config singleton."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
