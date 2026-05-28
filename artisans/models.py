import urllib.parse

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class VilleArtisan(models.Model):
    nom = models.CharField(max_length=90)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    region = models.CharField(max_length=90, blank=True)
    active = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Ville artisans"
        verbose_name_plural = "Villes artisans"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)[:110]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class MetierArtisan(models.Model):
    nom = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    icone = models.CharField(max_length=40, default="tools")
    description = models.CharField(max_length=240, blank=True)
    ordre = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Métier artisan"
        verbose_name_plural = "Métiers artisans"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class ProfilArtisan(models.Model):
    class TypeCompte(models.TextChoices):
        GRATUIT = "GRATUIT", "Gratuit"
        PREMIUM = "PREMIUM", "Premium"
        BUSINESS = "BUSINESS", "Business"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profil_artisan")
    nom_public = models.CharField(max_length=160)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    metiers = models.ManyToManyField(MetierArtisan, related_name="artisans")
    ville = models.ForeignKey(VilleArtisan, on_delete=models.PROTECT, related_name="artisans")
    quartier = models.CharField(max_length=120, blank=True)
    zone_intervention = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    telephone = models.CharField(max_length=30)
    whatsapp = models.CharField(max_length=30, blank=True)
    photo = models.ImageField(upload_to="artisans/profils/", null=True, blank=True)
    compte_type = models.CharField(max_length=20, choices=TypeCompte.choices, default=TypeCompte.GRATUIT)
    date_expiration_premium = models.DateField(null=True, blank=True)
    est_verifie = models.BooleanField(default=False)
    disponible_urgence = models.BooleanField(default=False)
    intervention_domicile = models.BooleanField(default=True)
    note_moyenne = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    nombre_avis = models.PositiveIntegerField(default=0)
    vues = models.PositiveIntegerField(default=0)
    contacts = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-compte_type", "-est_verifie", "-note_moyenne", "nom_public"]
        verbose_name = "Profil artisan"
        verbose_name_plural = "Profils artisans"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.nom_public}-{self.ville}")[:165] or "artisan"
            slug, n = base, 1
            while ProfilArtisan.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"[:190]
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom_public

    def get_absolute_url(self):
        return reverse("artisans:detail_artisan", kwargs={"slug": self.slug})

    @property
    def est_premium(self):
        if self.compte_type not in {self.TypeCompte.PREMIUM, self.TypeCompte.BUSINESS}:
            return False
        if self.date_expiration_premium and self.date_expiration_premium < timezone.now().date():
            return False
        return True

    @property
    def whatsapp_url(self):
        numero = (self.whatsapp or self.telephone).replace("+", "").replace(" ", "").replace("-", "")
        msg = f"Bonjour, je vous contacte depuis E-Shelle Artisans pour un besoin de travaux avec {self.nom_public}."
        return f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"

    @property
    def tel_url(self):
        return f"tel:{self.telephone}"


class RealisationArtisan(models.Model):
    artisan = models.ForeignKey(ProfilArtisan, on_delete=models.CASCADE, related_name="realisations")
    titre = models.CharField(max_length=160)
    image = models.ImageField(upload_to="artisans/realisations/")
    description = models.CharField(max_length=220, blank=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "id"]
        verbose_name = "Réalisation artisan"
        verbose_name_plural = "Réalisations artisans"

    def __str__(self):
        return f"{self.artisan} - {self.titre}"


class DemandeTravaux(models.Model):
    nom = models.CharField(max_length=120)
    telephone = models.CharField(max_length=30)
    ville = models.ForeignKey(VilleArtisan, on_delete=models.PROTECT, related_name="demandes")
    metier = models.ForeignKey(MetierArtisan, on_delete=models.SET_NULL, null=True, blank=True, related_name="demandes")
    quartier = models.CharField(max_length=120, blank=True)
    besoin = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    budget = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande de travaux"
        verbose_name_plural = "Demandes de travaux"

    def __str__(self):
        return f"{self.nom} - {self.besoin}"
