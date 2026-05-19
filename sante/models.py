import urllib.parse

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class VilleSante(models.Model):
    nom = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    region = models.CharField(max_length=80, blank=True)
    active = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Ville"
        verbose_name_plural = "Villes"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)[:100]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class CategorieSante(models.Model):
    class TypeCategorie(models.TextChoices):
        SERVICE = "SERVICE", "Service"
        PRODUIT = "PRODUIT", "Produit"
        SPECIALITE = "SPECIALITE", "Spécialité"

    nom = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    type_categorie = models.CharField(max_length=20, choices=TypeCategorie.choices, default=TypeCategorie.PRODUIT)
    icone = models.CharField(max_length=10, default="+")
    description = models.CharField(max_length=220, blank=True)
    ordre = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Catégorie santé"
        verbose_name_plural = "Catégories santé"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class ProfessionnelSante(models.Model):
    class TypePro(models.TextChoices):
        MEDECIN = "MEDECIN", "Médecin"
        CLINIQUE = "CLINIQUE", "Clinique"
        INFIRMIER = "INFIRMIER", "Infirmier"
        LABO = "LABO", "Laboratoire"
        KINE = "KINE", "Kinésithérapeute"
        BIEN_ETRE = "BIEN_ETRE", "Bien-être"

    nom = models.CharField(max_length=160)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    type_pro = models.CharField(max_length=20, choices=TypePro.choices, default=TypePro.CLINIQUE)
    specialites = models.ManyToManyField(CategorieSante, blank=True, related_name="professionnels")
    ville = models.ForeignKey(VilleSante, on_delete=models.PROTECT, related_name="professionnels")
    quartier = models.CharField(max_length=120, blank=True)
    adresse = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    telephone = models.CharField(max_length=30)
    whatsapp = models.CharField(max_length=30, blank=True, help_text="Numéro WhatsApp sans +")
    horaires = models.CharField(max_length=180, default="Lun-Sam 8h-18h")
    consultation_domicile = models.BooleanField(default=False)
    urgence = models.BooleanField(default=False)
    teleconsultation = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="profils_sante")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-is_verified", "nom"]
        verbose_name = "Professionnel santé"
        verbose_name_plural = "Professionnels santé"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.nom}-{self.ville}")[:180] or "sante"
            slug, n = base, 1
            while ProfessionnelSante.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"[:200]
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

    @property
    def whatsapp_url(self):
        numero = (self.whatsapp or self.telephone).replace("+", "").replace(" ", "").replace("-", "")
        msg = f"Bonjour, je vous contacte depuis E-Shelle Santé pour une information ou un rendez-vous avec {self.nom}."
        return f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"

    @property
    def tel_url(self):
        return f"tel:{self.telephone}"


class ProduitSante(models.Model):
    class TypeProduit(models.TextChoices):
        BIEN_ETRE = "BIEN_ETRE", "Bien-être"
        COMPLEMENT = "COMPLEMENT", "Complément"
        HYGIENE = "HYGIENE", "Hygiène"
        MATERIEL = "MATERIEL", "Matériel médical"
        BEBE = "BEBE", "Bébé & maman"
        SPORT = "SPORT", "Sport santé"

    titre = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    type_produit = models.CharField(max_length=20, choices=TypeProduit.choices, default=TypeProduit.BIEN_ETRE)
    categorie = models.ForeignKey(CategorieSante, on_delete=models.SET_NULL, null=True, blank=True, related_name="produits")
    description = models.TextField()
    image = models.ImageField(upload_to="sante/produits/", null=True, blank=True)
    ville = models.ForeignKey(VilleSante, on_delete=models.PROTECT, related_name="produits")
    vendeur_nom = models.CharField(max_length=140)
    telephone = models.CharField(max_length=30)
    whatsapp = models.CharField(max_length=30, blank=True, help_text="Numéro WhatsApp sans +")
    prix = models.PositiveIntegerField(default=0)
    prix_barre = models.PositiveIntegerField(null=True, blank=True)
    stock_disponible = models.PositiveIntegerField(default=1)
    livraison = models.BooleanField(default=False)
    ordonnance_requise = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="produits_sante")
    vues = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "is_verified", "created_at"]),
            models.Index(fields=["ville", "type_produit"]),
        ]
        verbose_name = "Produit santé"
        verbose_name_plural = "Produits santé"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.titre}-{self.ville}")[:190] or "produit-sante"
            slug, n = base, 1
            while ProduitSante.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"[:220]
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse("sante:detail_produit", kwargs={"slug": self.slug})

    @property
    def prix_display(self):
        if not self.prix:
            return "Prix à discuter"
        return f"{self.prix:,} FCFA".replace(",", " ")

    @property
    def reduction(self):
        if self.prix_barre and self.prix and self.prix_barre > self.prix:
            return int((1 - self.prix / self.prix_barre) * 100)
        return 0

    @property
    def whatsapp_url(self):
        numero = (self.whatsapp or self.telephone).replace("+", "").replace(" ", "").replace("-", "")
        msg = f"Bonjour, je suis intéressé par {self.titre} vu sur E-Shelle Santé."
        return f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"

    @property
    def tel_url(self):
        return f"tel:{self.telephone}"


class DemandeSante(models.Model):
    nom = models.CharField(max_length=120)
    telephone = models.CharField(max_length=30)
    ville = models.ForeignKey(VilleSante, on_delete=models.PROTECT, related_name="demandes")
    besoin = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande santé"
        verbose_name_plural = "Demandes santé"

    def __str__(self):
        return f"{self.nom} - {self.besoin}"
