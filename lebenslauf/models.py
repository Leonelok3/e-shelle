"""
Models pour la generation de CV allemand (Lebenslauf) assiste par IA.
- GermanCVProfile : profil candidat complet
- CVExperience    : experiences professionnelles
- CVEducation     : diplomes et formations
- CVLanguage      : niveaux de langues
- GeneratedLebenslauf : Lebenslauf genere et stocke
"""
from django.db import models
from django.conf import settings


class GermanCVProfile(models.Model):
    """Profil complet du candidat pour generer un Lebenslauf."""
    user         = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="german_cv_profile"
    )

    # Infos personnelles
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    email        = models.EmailField()
    phone        = models.CharField(max_length=30, blank=True)
    address      = models.CharField(max_length=300, blank=True,
                                    help_text="Adresse actuelle (pays + ville)")
    date_of_birth = models.DateField(null=True, blank=True)
    nationality  = models.CharField(max_length=100, default="Camerounaise")
    photo        = models.ImageField(upload_to="lebenslauf/photos/", blank=True, null=True,
                                     help_text="Photo professionnelle (obligatoire en Allemagne)")
    linkedin     = models.URLField(blank=True)

    # Niveau d'allemand declare
    GERMAN_LEVEL_CHOICES = [
        ("A1", "A1"), ("A2", "A2"), ("B1", "B1"), ("B2", "B2"), ("C1", "C1"), ("C2", "C2")
    ]
    german_level      = models.CharField(max_length=5, choices=GERMAN_LEVEL_CHOICES, default="B1")
    goethe_certified  = models.BooleanField(default=False,
                        help_text="Cocher si le certificat Goethe est deja obtenu")
    goethe_cert_date  = models.DateField(null=True, blank=True)

    # Objectif professionnel / secteur vise
    target_sector    = models.CharField(max_length=100, blank=True,
                        help_text="Ex: Gesundheit, Informatik, Mechatronik")
    target_cities    = models.CharField(max_length=300, blank=True,
                        help_text="Villes acceptees en Allemagne (ex: Berlin, Hamburg, Koeln)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil CV"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class CVExperience(models.Model):
    """Experience professionnelle pour le Lebenslauf."""
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="cv_experiences"
    )
    title       = models.CharField(max_length=200, help_text="Ex: Infirmier diplome d'Etat")
    company     = models.CharField(max_length=200, help_text="Nom de l'employeur")
    city        = models.CharField(max_length=100)
    country     = models.CharField(max_length=100, default="Cameroun")
    start_date  = models.DateField()
    end_date    = models.DateField(null=True, blank=True, help_text="Laisser vide si en cours")
    is_current  = models.BooleanField(default=False)
    description = models.TextField(blank=True,
                  help_text="Responsabilites principales (3-5 points).")
    order       = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Experience"

    def __str__(self):
        return f"{self.title} @ {self.company}"

    @property
    def period_display(self):
        """Format allemand : MM.YYYY – MM.YYYY"""
        start = self.start_date.strftime("%m.%Y")
        if self.is_current or not self.end_date:
            return f"{start} – heute"
        end = self.end_date.strftime("%m.%Y")
        return f"{start} – {end}"


class CVEducation(models.Model):
    """Diplome ou formation pour le Lebenslauf."""
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="cv_educations"
    )
    degree      = models.CharField(max_length=200, help_text="Ex: Licence en Informatique")
    school      = models.CharField(max_length=200, help_text="Nom de l'etablissement")
    city        = models.CharField(max_length=100)
    country     = models.CharField(max_length=100, default="Cameroun")
    start_year  = models.IntegerField()
    end_year    = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    order       = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-start_year"]
        verbose_name = "Formation"

    def __str__(self):
        return f"{self.degree} — {self.school}"


class CVLanguage(models.Model):
    """Niveau de langue pour le Lebenslauf."""
    PROFICIENCY_CHOICES = [
        ("Muttersprache",          "Langue maternelle"),
        ("verhandlungssicher",     "Courant (C1/C2)"),
        ("fliessend",              "Courant (B2)"),
        ("gute Kenntnisse",        "Bon niveau (B1)"),
        ("Grundkenntnisse",        "Notions (A1/A2)"),
    ]
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="cv_languages"
    )
    language    = models.CharField(max_length=50, help_text="Ex: Deutsch, Francais, Anglais")
    proficiency = models.CharField(max_length=30, choices=PROFICIENCY_CHOICES)
    certificate = models.CharField(max_length=100, blank=True,
                  help_text="Ex: Goethe-Zertifikat B1, DELF B2")

    class Meta:
        ordering = ["language"]
        verbose_name = "Langue"

    def __str__(self):
        return f"{self.language} — {self.proficiency}"


class GeneratedLebenslauf(models.Model):
    """Lebenslauf genere par IA, stocke pour telechargement."""
    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="lebenslauf_generated"
    )
    offer        = models.ForeignKey(
        "germany_opportunities.AusbildungOffer",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="lebenslauf_set"
    )
    # Offre libre si pas dans la base
    custom_offer_title   = models.CharField(max_length=300, blank=True)
    custom_offer_company = models.CharField(max_length=200, blank=True)

    content_html = models.TextField(help_text="HTML du Lebenslauf genere")
    content_pdf  = models.FileField(upload_to="lebenslauf/pdfs/", blank=True, null=True)

    ai_cover_letter = models.TextField(blank=True,
                      help_text="Lettre de motivation generee par IA (en allemand)")

    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lebenslauf genere"

    def __str__(self):
        target = self.offer or self.custom_offer_title or "libre"
        return f"Lebenslauf {self.user} → {target}"

    @property
    def offer_title(self):
        if self.offer:
            return self.offer.title
        return self.custom_offer_title or "Candidature spontanee"
