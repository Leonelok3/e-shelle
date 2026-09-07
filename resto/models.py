"""
E-Shelle Resto — Models
Restaurant discovery platform for Cameroon.
"""
import urllib.parse
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


# ──────────────────────────────────────────────────────────────────────────────
# Geography
# ──────────────────────────────────────────────────────────────────────────────

class City(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ville")
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        verbose_name = "Ville"
        verbose_name_plural = "Villes"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Neighborhood(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="neighborhoods", verbose_name="Ville")
    name = models.CharField(max_length=100, verbose_name="Quartier")
    slug = models.SlugField(max_length=120)

    class Meta:
        verbose_name = "Quartier"
        verbose_name_plural = "Quartiers"
        ordering = ["city", "name"]
        unique_together = ("city", "slug")

    def __str__(self):
        return f"{self.name} ({self.city.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Food Categories
# ──────────────────────────────────────────────────────────────────────────────

class FoodCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(max_length=10, default="🍽️", verbose_name="Icône (emoji)")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Catégorie alimentaire"
        verbose_name_plural = "Catégories alimentaires"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.icon} {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Restaurant
# ──────────────────────────────────────────────────────────────────────────────

class RestaurantQuerySet(models.QuerySet):
    def visible(self):
        """Restaurants reellement visibles publiquement : approuves, actifs
        et avec un abonnement en cours (non expire)."""
        return self.filter(
            is_approved=True,
            is_active=True,
            subscription__is_active=True,
            subscription__expiry_date__gte=timezone.localdate(),
        )


class Restaurant(models.Model):
    STATUS_CHOICES = [
        ("open", "Ouvert"),
        ("closed", "Fermé"),
        ("opening_soon", "Bientôt ouvert"),
    ]

    objects = RestaurantQuerySet.as_manager()

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurants",
        verbose_name="Propriétaire",
    )
    name = models.CharField(max_length=200, verbose_name="Nom du restaurant")
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True, verbose_name="Description")
    cover_image = models.ImageField(
        upload_to="resto/restaurants/",
        verbose_name="Photo de couverture",
        null=True, blank=True,
    )
    logo = models.ImageField(
        upload_to="resto/logos/",
        null=True, blank=True,
        verbose_name="Logo",
    )
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="restaurants", verbose_name="Ville")
    neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="restaurants",
        verbose_name="Quartier",
    )
    address = models.CharField(max_length=300, verbose_name="Adresse")
    phone = models.CharField(max_length=20, verbose_name="Téléphone (+237 6XX XX XX XX)")
    whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp (+237 6XX XX XX XX)")
    categories = models.ManyToManyField(FoodCategory, blank=True, verbose_name="Catégories")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="closed", verbose_name="Statut")
    opening_time = models.TimeField(verbose_name="Heure d'ouverture")
    closing_time = models.TimeField(verbose_name="Heure de fermeture")
    is_approved = models.BooleanField(default=False, verbose_name="Approuvé")
    is_featured = models.BooleanField(default=False, verbose_name="Mis en avant")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de vues")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"
        ordering = ["-is_featured", "-views_count", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            self.slug = base
            counter = 1
            while Restaurant.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def is_open_now(self) -> bool:
        now = timezone.localtime(timezone.now()).time()
        if self.opening_time <= self.closing_time:
            return self.opening_time <= now <= self.closing_time
        # Crosses midnight
        return now >= self.opening_time or now <= self.closing_time

    def whatsapp_url(self, dish_name: str = "") -> str:
        number = self.whatsapp.replace("+", "").replace(" ", "")
        if dish_name:
            msg = f"Bonjour, je voudrais commander : {dish_name} chez {self.name}. Est-ce disponible ?"
        else:
            msg = f"Bonjour, je voudrais passer une commande chez {self.name}."
        return f"https://wa.me/{number}?text={urllib.parse.quote(msg)}"

    def phone_url(self) -> str:
        return f"tel:{self.phone.replace(' ', '')}"

    @property
    def status_label(self) -> str:
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def status_color(self) -> str:
        return {
            "open": "green",
            "closed": "red",
            "opening_soon": "amber",
        }.get(self.status, "gray")


# ──────────────────────────────────────────────────────────────────────────────
# Subscription
# ──────────────────────────────────────────────────────────────────────────────

class Subscription(models.Model):
    PLAN_CHOICES = [
        ("free_trial", "Essai gratuit (30 jours)"),
        ("basic", "Basic"),
        ("premium", "Premium"),
    ]

    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="Restaurant",
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free_trial", verbose_name="Plan")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(verbose_name="Date d'expiration")
    auto_renew = models.BooleanField(default=False, verbose_name="Renouvellement auto")

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"

    def __str__(self):
        return f"{self.restaurant.name} — {self.get_plan_display()}"

    @property
    def days_remaining(self) -> int:
        delta = self.expiry_date - date.today()
        return max(0, delta.days)

    @property
    def is_expired(self) -> bool:
        return date.today() > self.expiry_date


# ──────────────────────────────────────────────────────────────────────────────
# Menu
# ──────────────────────────────────────────────────────────────────────────────

class MenuCategory(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_categories",
        verbose_name="Restaurant",
    )
    name = models.CharField(max_length=100, verbose_name="Nom de la catégorie")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Catégorie du menu"
        verbose_name_plural = "Catégories du menu"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.restaurant.name} — {self.name}"


class Dish(models.Model):
    AVAILABILITY_CHOICES = [
        ("available", "Disponible"),
        ("in_x_minutes", "Disponible dans X minutes"),
        ("unavailable", "Indisponible"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="dishes",
        verbose_name="Restaurant",
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="dishes",
        verbose_name="Catégorie",
    )
    name = models.CharField(max_length=200, verbose_name="Nom du plat")
    description = models.TextField(blank=True, verbose_name="Description")
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Prix (FCFA)")
    image = models.ImageField(
        upload_to="resto/dishes/",
        blank=True, null=True,
        verbose_name="Photo du plat",
    )
    availability = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default="available",
        verbose_name="Disponibilité",
    )
    available_in_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Disponible dans (minutes)",
    )
    is_popular = models.BooleanField(default=False, verbose_name="Plat populaire")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Plat"
        verbose_name_plural = "Plats"
        ordering = ["category", "order", "name"]

    def __str__(self):
        return f"{self.name} — {self.formatted_price}"

    @property
    def formatted_price(self) -> str:
        price_int = int(self.price)
        # French thousands separator
        return f"{price_int:,}".replace(",", " ") + " FCFA"

    @property
    def availability_label(self) -> str:
        if self.availability == "in_x_minutes" and self.available_in_minutes:
            return f"Dans {self.available_in_minutes} min"
        return dict(self.AVAILABILITY_CHOICES).get(self.availability, "")

    @property
    def availability_color(self) -> str:
        return {
            "available": "green",
            "in_x_minutes": "amber",
            "unavailable": "red",
        }.get(self.availability, "gray")


# ──────────────────────────────────────────────────────────────────────────────
# Tracking
# ──────────────────────────────────────────────────────────────────────────────

class ContactLog(models.Model):
    ACTION_CHOICES = [
        ("call", "Appel téléphonique"),
        ("whatsapp", "Message WhatsApp"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="contact_logs",
        verbose_name="Restaurant",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    dish = models.ForeignKey(
        Dish,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Plat concerné",
    )
    session_key = models.CharField(max_length=64, blank=True, verbose_name="Session")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.restaurant.name} — {self.get_action_display()} ({self.created_at:%d/%m/%Y})"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resto_favorites",
        verbose_name="Utilisateur",
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Restaurant",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        unique_together = ("user", "restaurant")

    def __str__(self):
        return f"{self.user} ❤️ {self.restaurant.name}"


# ──────────────────────────────────────────────────────────────────────────────
# Reviews — Système d'avis clients
# ──────────────────────────────────────────────────────────────────────────────

class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1 to 5 stars

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Restaurant",
    )
    author_name = models.CharField(max_length=100, verbose_name="Votre prénom")
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name="Note (1 à 5 étoiles)",
    )
    comment = models.TextField(
        max_length=800,
        verbose_name="Votre avis",
        help_text="Partagez votre expérience (max 800 caractères)",
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Approuvé",
        help_text="Seuls les avis approuvés sont visibles publiquement.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis clients"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author_name} — {self.restaurant.name} ({self.rating}★)"

    @property
    def stars_full(self):
        return range(self.rating)

    @property
    def stars_empty(self):
        return range(5 - self.rating)


# ──────────────────────────────────────────────────────────────────────────────
# Notifications — Alertes internes pour les restaurateurs
# ──────────────────────────────────────────────────────────────────────────────

class Notification(models.Model):
    TYPE_CHOICES = [
        ("contact_whatsapp", "Nouveau contact WhatsApp"),
        ("contact_call",     "Nouveau appel"),
        ("new_review",       "Nouvel avis client"),
        ("subscription",     "Abonnement"),
        ("system",           "Système"),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Restaurant",
    )
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Type")
    message = models.TextField(verbose_name="Message")
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.restaurant.name} — {self.get_type_display()}"


# ──────────────────────────────────────────────────────────────────────────────
# Hero Banner — Slideshow géré depuis l'admin
# ──────────────────────────────────────────────────────────────────────────────

class HeroBanner(models.Model):
    """
    Bannière hero affichée en slideshow sur la page d'accueil.
    Supporte images ET vidéos. Géré entièrement depuis l'admin Django.
    """
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Vidéo"),
    ]

    TAG_CHOICES = [
        ("", "Aucun"),
        ("nouveau", "Nouveau"),
        ("premium", "Premium"),
        ("promo", "Promotion"),
        ("vedette", "Vedette"),
        ("exclusif", "Exclusif"),
    ]

    # ── Contenu ──────────────────────────────────────────────────────
    title = models.CharField(
        max_length=100, blank=True,
        verbose_name="Titre (optionnel)",
        help_text="Ex : Chez Mama Fouda · Yaoundé",
    )
    subtitle = models.CharField(
        max_length=200, blank=True,
        verbose_name="Sous-titre (optionnel)",
        help_text="Ex : Ndolé aux crevettes — 2 500 FCFA",
    )
    tag = models.CharField(
        max_length=20, choices=TAG_CHOICES, blank=True,
        verbose_name="Badge",
        help_text="Petit badge coloré affiché en haut à gauche de la bannière",
    )

    # ── Médias ───────────────────────────────────────────────────────
    media_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, default="image",
        verbose_name="Type de média",
    )
    image = models.ImageField(
        upload_to="resto/banners/",
        blank=True, null=True,
        verbose_name="Image",
        help_text="Recommandé : 1200×600px, JPG ou WebP. Max 5 Mo.",
    )
    video = models.FileField(
        upload_to="resto/banners/videos/",
        blank=True, null=True,
        verbose_name="Vidéo",
        help_text="Format MP4 recommandé. Max 50 Mo. Lecture auto, muette.",
    )
    video_poster = models.ImageField(
        upload_to="resto/banners/posters/",
        blank=True, null=True,
        verbose_name="Miniature vidéo",
        help_text="Image affichée avant le chargement de la vidéo.",
    )

    # ── Lien CTA ─────────────────────────────────────────────────────
    cta_label = models.CharField(
        max_length=60, blank=True,
        verbose_name="Texte du bouton CTA",
        help_text="Ex : Voir le menu · Commander maintenant",
    )
    cta_url = models.CharField(
        max_length=300, blank=True,
        verbose_name="URL du bouton CTA",
        help_text="URL interne (ex: /resto/r/chez-mama-fouda/) ou externe",
    )

    # ── Restaurant lié (optionnel) ────────────────────────────────────
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="banners",
        verbose_name="Restaurant associé",
        help_text="Si renseigné, le CTA pointe automatiquement vers la page du restaurant.",
    )

    # ── Paramètres d'affichage ────────────────────────────────────────
    duration = models.PositiveIntegerField(
        default=5,
        verbose_name="Durée d'affichage (secondes)",
        help_text="Temps avant passage automatique au slide suivant.",
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    is_active = models.BooleanField(default=True, verbose_name="Actif")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bannière hero"
        verbose_name_plural = "Bannières hero"
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.title or f"Bannière #{self.pk}"

    @property
    def resolved_cta_url(self):
        """Return CTA URL: use restaurant page if linked, else manual URL."""
        if self.restaurant:
            return f"/resto/r/{self.restaurant.slug}/"
        return self.cta_url or ""

    @property
    def tag_color(self):
        """Tailwind background color class for tag badge."""
        colors = {
            "nouveau":  "bg-blue-500",
            "premium":  "bg-amber-500",
            "promo":    "bg-red-500",
            "vedette":  "bg-purple-500",
            "exclusif": "bg-gray-900",
        }
        return colors.get(self.tag, "bg-gray-500")

    @property
    def tag_label(self):
        return dict(self.TAG_CHOICES).get(self.tag, "")
