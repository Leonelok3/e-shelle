from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from core.constants import LEVEL_CHOICES


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom de la catégorie"
    )
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # 🆕 NIVEAU DE LANGUE (A1 → C2)
    level = models.CharField(
        max_length=2,
        choices=LEVEL_CHOICES,
        default="A1",
        db_index=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="Métier / Catégorie"
    )

    headline = models.CharField(
        max_length=200,
        blank=True,
        help_text="Ex: Menuisier Expert | Comptable Senior",
        verbose_name="Titre du profil"
    )

    bio = models.TextField(
        blank=True,
        verbose_name="À propos"
    )

    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ville / Localisation"
    )

    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )

    linkedin_url = models.URLField(
        blank=True,
        verbose_name="Lien LinkedIn"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profil de {self.user.username}"

    def get_absolute_url(self):
        return reverse("profiles:detail", kwargs={"pk": self.pk})


class PortfolioItem(models.Model):
    ITEM_TYPES = (
        ("cv", "CV (PDF)"),
        ("image", "Photo de réalisation"),
        ("ref", "Lettre de recommandation"),
    )

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="portfolio_items"
    )

    title = models.CharField(
        max_length=100,
        verbose_name="Titre du document"
    )

    file = models.FileField(
        upload_to="portfolio/",
        verbose_name="Fichier"
    )

    item_type = models.CharField(
        max_length=10,
        choices=ITEM_TYPES,
        default="image",
        verbose_name="Type"
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    def __str__(self):
        return self.title
