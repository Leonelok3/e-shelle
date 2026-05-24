from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid


class FacebookPageConfig(models.Model):
    """Configuration de la page Facebook E-Shelle."""

    page_id = models.CharField(max_length=100, unique=True, verbose_name="Page ID")
    page_name = models.CharField(max_length=255, verbose_name="Nom de la page")
    page_access_token = models.TextField(verbose_name="Token d'accès page")
    app_id = models.CharField(max_length=100, blank=True, verbose_name="App ID Meta")
    app_secret = models.CharField(max_length=255, blank=True, verbose_name="App Secret Meta")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    token_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expiration du token")
    last_token_refresh = models.DateTimeField(null=True, blank=True, verbose_name="Dernier refresh token")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration Page Facebook"
        verbose_name_plural = "Configurations Pages Facebook"

    def __str__(self):
        return f"{self.page_name} ({self.page_id})"

    def is_token_valid(self):
        if not self.token_expires_at:
            return True  # Token permanent supposé valide
        return timezone.now() < self.token_expires_at


class ContentRule(models.Model):
    """Règles de génération de contenu par section de l'app."""

    SECTION_CHOICES = [
        ("annonces", "Annonces Générales"),
        ("immobilier", "Immobilier"),
        ("auto", "Automobiles"),
        ("agro", "Agriculture"),
        ("rencontres", "Rencontres E-Shelle Love"),
        ("njangi", "Njangi / Tontine"),
        ("edu", "Éducation"),
        ("promo", "Promotions & Offres"),
        ("general", "Contenu Général"),
        ("resto", "Restaurants"),
        ("services", "Services"),
        ("gaz", "Gaz domestique"),
        ("pressing", "Pressing"),
        ("sante", "Santé / Pharmacies"),
        ("jobs", "Jobs / Emplois"),
        ("business", "Prestataires E-Shelle"),
        ("chat_ai", "Chat IA E-Shelle"),
    ]

    TONE_CHOICES = [
        ("professionnel", "Professionnel"),
        ("amical", "Amical & Chaleureux"),
        ("romantique", "Romantique"),
        ("informatif", "Informatif"),
        ("dynamique", "Dynamique & Energique"),
        ("inspirant", "Inspirant"),
    ]

    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True, verbose_name="Section")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    tone = models.CharField(max_length=30, choices=TONE_CHOICES, default="amical", verbose_name="Ton")
    post_frequency_per_day = models.PositiveSmallIntegerField(default=1, verbose_name="Posts par jour")
    preferred_hours = models.CharField(
        max_length=100,
        default="08:00,12:00,18:00",
        help_text="Heures de publication séparées par virgule (ex: 08:00,12:00)",
        verbose_name="Heures préférées",
    )
    custom_instructions = models.TextField(
        blank=True,
        help_text="Instructions spéciales pour l'agent IA",
        verbose_name="Instructions personnalisées",
    )
    include_emoji = models.BooleanField(default=True, verbose_name="Inclure des emojis")
    include_hashtags = models.BooleanField(default=True, verbose_name="Inclure des hashtags")
    max_post_length = models.PositiveIntegerField(default=500, verbose_name="Longueur max du post (caractères)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Règle de Contenu"
        verbose_name_plural = "Règles de Contenu"
        ordering = ["section"]

    def __str__(self):
        return f"Règle {self.get_section_display()} ({self.tone})"

    def get_preferred_hours_list(self):
        return [h.strip() for h in self.preferred_hours.split(",") if h.strip()]


class PostTemplate(models.Model):
    """Templates de posts réutilisables."""

    TEMPLATE_TYPE_CHOICES = [
        ("texte", "Texte simple"),
        ("lien", "Lien avec aperçu"),
        ("photo", "Photo + texte"),
        ("carousel", "Carrousel"),
    ]

    name = models.CharField(max_length=100, verbose_name="Nom du template")
    section = models.CharField(
        max_length=50,
        choices=ContentRule.SECTION_CHOICES,
        verbose_name="Section",
    )
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, default="texte")
    template_body = models.TextField(
        help_text="Utilisez {variable} pour les variables dynamiques",
        verbose_name="Corps du template",
    )
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0, verbose_name="Nombre d'utilisations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Template de Post"
        verbose_name_plural = "Templates de Posts"
        ordering = ["-usage_count"]

    def __str__(self):
        return f"{self.name} ({self.get_section_display()})"


class ScheduledPost(models.Model):
    """Posts planifiés en attente de publication."""

    STATUS_CHOICES = [
        ("en_attente", "En attente"),
        ("approuve", "Approuvé"),
        ("publie", "Publié"),
        ("echec", "Échec"),
        ("annule", "Annulé"),
    ]

    SECTION_CHOICES = ContentRule.SECTION_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page_config = models.ForeignKey(
        FacebookPageConfig, on_delete=models.CASCADE, related_name="scheduled_posts"
    )
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, verbose_name="Section")
    title = models.CharField(max_length=255, verbose_name="Titre interne")
    content = models.TextField(verbose_name="Contenu du post")
    image_url = models.URLField(blank=True, verbose_name="URL de l'image")
    link_url = models.URLField(blank=True, verbose_name="URL du lien")
    scheduled_at = models.DateTimeField(verbose_name="Heure de publication planifiée")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="en_attente")
    requires_approval = models.BooleanField(default=False, verbose_name="Requiert une approbation")
    ai_generated = models.BooleanField(default=True, verbose_name="Généré par IA")
    source_object_id = models.CharField(
        max_length=50, blank=True, verbose_name="ID de l'objet source"
    )
    source_object_type = models.CharField(
        max_length=50, blank=True, verbose_name="Type de l'objet source"
    )
    retry_count = models.PositiveSmallIntegerField(default=0, verbose_name="Nombre de tentatives")
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Post Planifié"
        verbose_name_plural = "Posts Planifiés"
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"[{self.get_section_display()}] {self.title} - {self.scheduled_at.strftime('%d/%m/%Y %H:%M')}"

    def is_ready(self):
        return (
            self.status in ("en_attente", "approuve")
            and self.scheduled_at <= timezone.now()
        )


class PublishedPost(models.Model):
    """Historique des posts publiés avec succès."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheduled_post = models.OneToOneField(
        ScheduledPost,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published",
    )
    page_config = models.ForeignKey(
        FacebookPageConfig, on_delete=models.CASCADE, related_name="published_posts"
    )
    section = models.CharField(max_length=50, choices=ContentRule.SECTION_CHOICES)
    facebook_post_id = models.CharField(max_length=100, unique=True, verbose_name="ID du post Facebook")
    content = models.TextField(verbose_name="Contenu publié")
    image_url = models.URLField(blank=True)
    link_url = models.URLField(blank=True)
    published_at = models.DateTimeField(auto_now_add=True, verbose_name="Publié le")

    # Statistiques (mis à jour par la tâche de sync)
    likes_count = models.PositiveIntegerField(default=0, verbose_name="Likes")
    comments_count = models.PositiveIntegerField(default=0, verbose_name="Commentaires")
    shares_count = models.PositiveIntegerField(default=0, verbose_name="Partages")
    reach = models.PositiveIntegerField(default=0, verbose_name="Portée")
    stats_updated_at = models.DateTimeField(null=True, blank=True, verbose_name="Stats mises à jour le")

    class Meta:
        verbose_name = "Post Publié"
        verbose_name_plural = "Posts Publiés"
        ordering = ["-published_at"]

    def __str__(self):
        return f"FB:{self.facebook_post_id} [{self.get_section_display()}] {self.published_at.strftime('%d/%m/%Y %H:%M')}"

    def get_facebook_url(self):
        return f"https://www.facebook.com/{self.facebook_post_id}"


class AgentLog(models.Model):
    """Journal d'activité des agents IA."""

    LOG_LEVEL_CHOICES = [
        ("info", "Info"),
        ("success", "Succès"),
        ("warning", "Avertissement"),
        ("error", "Erreur"),
    ]

    ACTION_CHOICES = [
        ("generate_content", "Génération de contenu"),
        ("publish_post", "Publication de post"),
        ("schedule_post", "Planification de post"),
        ("refresh_token", "Rafraîchissement du token"),
        ("sync_stats", "Synchronisation des stats"),
        ("agent_run", "Exécution de l'agent"),
        ("token_check", "Vérification du token"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.CharField(max_length=50, blank=True, verbose_name="Section")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name="Action")
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES, default="info")
    message = models.TextField(verbose_name="Message")
    details = models.JSONField(default=dict, blank=True, verbose_name="Détails JSON")
    duration_ms = models.PositiveIntegerField(null=True, blank=True, verbose_name="Durée (ms)")
    tokens_used = models.PositiveIntegerField(default=0, verbose_name="Tokens IA utilisés")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log Agent"
        verbose_name_plural = "Logs Agents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.level.upper()}] {self.get_action_display()} - {self.created_at.strftime('%d/%m/%Y %H:%M:%S')}"


class AgentStats(models.Model):
    """Statistiques journalières agrégées des agents."""

    date = models.DateField(unique=True, verbose_name="Date")
    total_posts_generated = models.PositiveIntegerField(default=0, verbose_name="Posts générés")
    total_posts_published = models.PositiveIntegerField(default=0, verbose_name="Posts publiés")
    total_posts_failed = models.PositiveIntegerField(default=0, verbose_name="Posts échoués")
    total_tokens_used = models.PositiveIntegerField(default=0, verbose_name="Tokens IA utilisés")
    posts_by_section = models.JSONField(default=dict, blank=True, verbose_name="Posts par section")
    total_reach = models.PositiveIntegerField(default=0, verbose_name="Portée totale")
    total_likes = models.PositiveIntegerField(default=0, verbose_name="Likes totaux")
    total_comments = models.PositiveIntegerField(default=0, verbose_name="Commentaires totaux")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Statistiques Agent"
        verbose_name_plural = "Statistiques Agents"
        ordering = ["-date"]

    def __str__(self):
        return f"Stats du {self.date.strftime('%d/%m/%Y')} — {self.total_posts_published} publiés"
