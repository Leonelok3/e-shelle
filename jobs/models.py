import urllib.parse
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class SecteurJob(models.Model):
    nom = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    active = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Secteur"
        verbose_name_plural = "Secteurs"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)[:100]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class VilleJob(models.Model):
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


class OffreJob(models.Model):
    class TypeContrat(models.TextChoices):
        CDI = "CDI", "CDI"
        CDD = "CDD", "CDD"
        STAGE = "STAGE", "Stage"
        MISSION = "MISSION", "Mission"
        JOURNALIER = "JOURNALIER", "Journalier"
        FREELANCE = "FREELANCE", "Freelance"

    class ModeTravail(models.TextChoices):
        SUR_SITE = "SUR_SITE", "Sur site"
        HYBRIDE = "HYBRIDE", "Hybride"
        DISTANCE = "DISTANCE", "A distance"

    titre = models.CharField(max_length=160)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    entreprise = models.CharField(max_length=140)
    logo = models.ImageField(upload_to="jobs/logos/", blank=True, null=True)
    secteur = models.ForeignKey(SecteurJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="offres")
    ville = models.ForeignKey(VilleJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="offres")
    quartier = models.CharField(max_length=120, blank=True)
    type_contrat = models.CharField(max_length=20, choices=TypeContrat.choices, default=TypeContrat.CDI)
    mode_travail = models.CharField(max_length=20, choices=ModeTravail.choices, default=ModeTravail.SUR_SITE)
    salaire_min = models.PositiveIntegerField(null=True, blank=True)
    salaire_max = models.PositiveIntegerField(null=True, blank=True)
    devise = models.CharField(max_length=10, default="XAF")
    description = models.TextField()
    missions = models.TextField(blank=True)
    profil_recherche = models.TextField(blank=True)
    avantages = models.TextField(blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True, help_text="Numero WhatsApp sans +, ex: 237680625082")
    email = models.EmailField(blank=True)
    lien_externe = models.URLField(blank=True)
    date_limite = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    vues = models.PositiveIntegerField(default=0)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="offres_jobs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-is_verified", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "type_contrat", "created_at"]),
            models.Index(fields=["ville", "secteur", "is_active"]),
        ]
        verbose_name = "Offre d'emploi"
        verbose_name_plural = "Offres d'emploi"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.titre}-{self.entreprise}")[:190] or "offre"
            slug, n = base, 1
            while OffreJob.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"[:220]
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titre} - {self.entreprise}"

    def get_absolute_url(self):
        return reverse("jobs:detail", kwargs={"slug": self.slug})

    @property
    def salaire_display(self):
        if self.salaire_min and self.salaire_max:
            return f"{self.salaire_min:,} - {self.salaire_max:,} {self.devise}".replace(",", " ")
        if self.salaire_min:
            return f"A partir de {self.salaire_min:,} {self.devise}".replace(",", " ")
        return "Salaire a discuter"

    @property
    def est_expiree(self):
        return bool(self.date_limite and self.date_limite < timezone.localdate())

    @property
    def whatsapp_url(self):
        numero = (self.whatsapp or self.telephone).replace("+", "").replace(" ", "").replace("-", "")
        msg = f"Bonjour, je suis interesse par l'offre {self.titre} chez {self.entreprise} vue sur E-Shelle Jobs."
        return f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"

    @property
    def tel_url(self):
        return f"tel:{self.telephone}"


class CandidatureJob(models.Model):
    offre = models.ForeignKey(OffreJob, on_delete=models.CASCADE, related_name="candidatures")
    nom = models.CharField(max_length=140)
    telephone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    ville = models.CharField(max_length=80, blank=True)
    message = models.TextField(blank=True)
    cv = models.FileField(upload_to="jobs/cv/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Candidature"
        verbose_name_plural = "Candidatures"

    def __str__(self):
        return f"{self.nom} -> {self.offre.titre}"


class CanadaJobOffer(models.Model):
    """
    Offres d'emploi d'employeurs canadiens qui recrutent à l'étranger.
    Recherchées globalement et enrichies par l'IA.
    """
    ref_nr = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=300)
    company = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    
    lmia_status = models.CharField(
        max_length=50, 
        default="Non précisé",
        help_text="EIMT approuvé, EIMT en cours, exempté ou non précisé"
    )
    
    salary = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    url_apply = models.URLField(max_length=500)
    
    # Enrichissement IA
    ai_summary_fr = models.TextField(blank=True, help_text="Résumé de l'offre par l'IA")
    
    is_active = models.BooleanField(default=True, db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fetched_at"]
        verbose_name = "Offre Canada"
        verbose_name_plural = "Offres Canada"

    def __str__(self):
        return f"{self.title} — {self.company} ({self.city}, {self.province})"

    @property
    def is_new(self):
        from django.utils import timezone
        import datetime
        return (timezone.now() - self.fetched_at) < datetime.timedelta(hours=48)

