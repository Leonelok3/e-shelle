from django.db import models
from django.conf import settings
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
        ordering = ["name"]

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=80, unique=True, db_index=True)

    class Meta:
        verbose_name = "Compétence"
        verbose_name_plural = "Compétences"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # Niveau de langue (A1 → C2)
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

    # Publication contrôlée (visible recruteurs uniquement si premium actif)
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Profil publié"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    skills = models.ManyToManyField(
        Skill,
        through="ProfileSkill",
        blank=True,
        related_name="profiles"
    )

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Profil de {self.user.username}"

    def get_absolute_url(self):
        return reverse("profiles:detail", kwargs={"pk": self.pk})


class ProfileSkill(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    # niveau 1-5 simple
    level = models.PositiveSmallIntegerField(default=3)
    years = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("profile", "skill")
        verbose_name = "Compétence du profil"
        verbose_name_plural = "Compétences du profil"

    def __str__(self):
        return f"{self.profile.user.username} - {self.skill.name}"


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

    class Meta:
        verbose_name = "Élément de portfolio"
        verbose_name_plural = "Éléments de portfolio"
        ordering = ["-id"]

    def __str__(self):
        return self.title


class RecruiterFavorite(models.Model):
    recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_favorites",
        verbose_name="Recruteur (utilisateur)"
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Profil favori"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("recruiter", "profile")
        verbose_name = "Favori recruteur"
        verbose_name_plural = "Favoris recruteur"

    def __str__(self):
        return f"{self.recruiter} → {self.profile}"
