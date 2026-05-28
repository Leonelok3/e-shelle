"""
AdGen — Advertising Content Generator
Modèles de données
"""
from django.db import models
from django.conf import settings


PAYS_CHOICES = [
    ("cm", "Cameroun"),
    ("ci", "Côte d'Ivoire"),
    ("sn", "Sénégal"),
    ("cd", "RD Congo"),
    ("ga", "Gabon"),
    ("ng", "Nigeria"),
    ("gh", "Ghana"),
    ("bj", "Bénin"),
    ("ml", "Mali"),
    ("bf", "Burkina Faso"),
]

VILLE_CHOICES = [
    ("", "Choisir une ville"),
    ("douala", "Douala"),
    ("yaounde", "Yaoundé"),
    ("bafoussam", "Bafoussam"),
    ("bamenda", "Bamenda"),
    ("garoua", "Garoua"),
    ("maroua", "Maroua"),
    ("bertoua", "Bertoua"),
    ("limbe", "Limbé"),
    ("kribi", "Kribi"),
    ("ebolowa", "Ebolowa"),
    ("abidjan", "Abidjan"),
    ("dakar", "Dakar"),
    ("kinshasa", "Kinshasa"),
    ("libreville", "Libreville"),
    ("cotonou", "Cotonou"),
    ("bamako", "Bamako"),
    ("ouagadougou", "Ouagadougou"),
    ("accra", "Accra"),
    ("lagos", "Lagos"),
    ("autre", "Autre ville"),
]

STATUS_CHOICES = [
    ("pending",    "En attente"),
    ("processing", "En cours"),
    ("done",       "Terminé"),
    ("failed",     "Échec"),
]


class AdModule(models.Model):
    """Module de génération disponible (configurable via admin)."""
    slug        = models.CharField(max_length=30, unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=10, default="✨")
    is_active   = models.BooleanField(default=True)
    is_premium  = models.BooleanField(default=False)
    order       = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        ordering = ["order"]

    def __str__(self):
        return self.name


class AdCampaign(models.Model):
    """Une campagne = un produit soumis pour génération."""
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ad_campaigns")
    nom_produit      = models.CharField(max_length=200, verbose_name="Nom du produit")
    description      = models.TextField(verbose_name="Description du produit")
    prix             = models.CharField(max_length=50, verbose_name="Prix")
    cible            = models.CharField(max_length=200, verbose_name="Cible / audience")
    pays             = models.CharField(max_length=5, choices=PAYS_CHOICES, default="cm", verbose_name="Pays cible")
    ville            = models.CharField(max_length=80, blank=True, verbose_name="Ville cible")
    modules_selected = models.JSONField(default=list, verbose_name="Modules sélectionnés")
    status           = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Campagne"
        verbose_name_plural = "Campagnes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nom_produit} — {self.user} ({self.get_status_display()})"

    @property
    def is_done(self):
        return self.status == "done"

    @property
    def pays_label(self):
        return dict(PAYS_CHOICES).get(self.pays, self.pays)

    @property
    def ville_label(self):
        if not self.ville:
            return "Toutes les villes"
        return dict(VILLE_CHOICES).get(self.ville, self.ville.title())


class AdContent(models.Model):
    """Contenu généré pour une campagne."""
    campaign             = models.OneToOneField(AdCampaign, on_delete=models.CASCADE, related_name="content")

    # Titres & description
    titles               = models.JSONField(default=list, blank=True)
    description_generated = models.TextField(blank=True)
    benefits             = models.JSONField(default=list, blank=True)

    # Social media
    facebook_post        = models.TextField(blank=True)
    instagram_post       = models.TextField(blank=True)
    whatsapp_message     = models.TextField(blank=True)
    hashtags             = models.JSONField(default=list, blank=True)

    # TikTok
    tiktok_script        = models.TextField(blank=True)
    voice_over           = models.TextField(blank=True)

    # Chatbot
    chatbot_reply        = models.TextField(blank=True)

    # Méta
    raw_json             = models.JSONField(default=dict, blank=True)
    generated_at         = models.DateTimeField(auto_now_add=True)
    tokens_used          = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Contenu généré"
        verbose_name_plural = "Contenus générés"

    def __str__(self):
        return f"Contenu — {self.campaign.nom_produit}"


class AdUsageStat(models.Model):
    """Statistiques d'utilisation par utilisateur."""
    user              = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adgen_stats")
    campaigns_count   = models.IntegerField(default=0)
    tokens_total      = models.IntegerField(default=0)
    last_generation   = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Stat utilisateur"
        verbose_name_plural = "Stats utilisateurs"

    def __str__(self):
        return f"Stats — {self.user}"

    @property
    def campaigns_remaining(self):
        from django.conf import settings
        limit = getattr(settings, "ADGEN_MAX_CAMPAIGNS_FREE", 5)
        return max(0, limit - self.campaigns_count)
