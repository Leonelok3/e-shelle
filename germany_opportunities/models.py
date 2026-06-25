"""
Models pour les opportunites en Allemagne :
- AusbildungOffer : offres de formation en alternance (API Bundesagentur)
- ScholarshipOpportunity : bourses d'etudes (DAAD, etc.)
- UserOpportunityBookmark : sauvegardes de l'utilisateur
"""
from django.db import models
from django.conf import settings


class AusbildungOffer(models.Model):
    """
    Offre d'Ausbildung (formation en alternance) recuperee via l'API
    officielle de la Bundesagentur fuer Arbeit.
    Mise a jour quotidiennement par la tache Celery fetch_ausbildung_offers.
    """
    SECTOR_CHOICES = [
        ("gesundheit",   "Gesundheit & Pflege (Sante)"),
        ("it",           "IT & Informatik"),
        ("elektro",      "Elektrotechnik & Mechatronik"),
        ("bau",          "Bau & Handwerk"),
        ("hotellerie",   "Hotellerie & Gastronomie"),
        ("logistik",     "Logistik & Transport"),
        ("kaufmann",     "Kaufmann / Buero"),
        ("soziales",     "Soziales & Erziehung"),
        ("andere",       "Autre"),
    ]

    LANGUAGE_CHOICES = [
        ("B1", "B1 (intermediaire)"),
        ("B2", "B2 (intermediaire superieur)"),
        ("C1", "C1 (avance)"),
        ("A2", "A2 (elementaire)"),
    ]

    # Identifiant unique cote Bundesagentur
    ref_nr          = models.CharField(max_length=100, unique=True, db_index=True)

    # Infos principales
    title           = models.CharField(max_length=300)
    company         = models.CharField(max_length=200)
    city            = models.CharField(max_length=100)
    postal_code     = models.CharField(max_length=10, blank=True)
    region          = models.CharField(max_length=100, blank=True)  # Bundesland
    sector          = models.CharField(max_length=20, choices=SECTOR_CHOICES, default="andere")

    # Conditions
    start_date      = models.DateField(null=True, blank=True)
    salary_month    = models.CharField(max_length=50, blank=True)   # ex: "620-800 EUR"
    language_req    = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="B1")
    duration_months = models.IntegerField(default=36)               # duree de la formation

    # Contenu
    description     = models.TextField(blank=True)
    url_apply       = models.URLField(max_length=500)

    # Enrichissement IA
    ai_summary_fr   = models.TextField(blank=True,
        help_text="Resume en francais genere par GPT pour les candidats africains")
    ai_tips_fr      = models.TextField(blank=True,
        help_text="Conseils de candidature specifiques generes par IA")

    # Metadonnees
    is_active       = models.BooleanField(default=True, db_index=True)
    fetched_at      = models.DateTimeField(auto_now_add=True)
    last_seen       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fetched_at"]
        verbose_name = "Offre Ausbildung"
        verbose_name_plural = "Offres Ausbildung"
        indexes = [
            models.Index(fields=["is_active", "sector"]),
            models.Index(fields=["is_active", "language_req"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.company} ({self.city})"

    @property
    def is_new(self):
        """True si l'offre a ete recuperee il y a moins de 48h."""
        from django.utils import timezone
        import datetime
        return (timezone.now() - self.fetched_at) < datetime.timedelta(hours=48)

    @property
    def salary_display(self):
        return self.salary_month or "Selon convention"


class ScholarshipOpportunity(models.Model):
    """
    Bourse d'etude ou de formation en Allemagne.
    Sources : DAAD, Goethe-Institut, fondations allemandes, etc.
    """
    LEVEL_CHOICES = [
        ("ausbildung", "Ausbildung (Formation pro)"),
        ("bachelor",   "Licence"),
        ("master",     "Master"),
        ("phd",        "Doctorat"),
        ("research",   "Recherche"),
        ("language",   "Cours de langue"),
    ]

    title       = models.CharField(max_length=300)
    provider    = models.CharField(max_length=200)           # DAAD, Goethe, etc.
    level       = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    deadline    = models.DateField(null=True, blank=True)
    amount      = models.CharField(max_length=200, blank=True)  # ex: "934 EUR/mois"
    description = models.TextField()
    url         = models.URLField(max_length=500)

    # Pays eligibles (JSON list sous forme de texte CSV)
    countries   = models.CharField(max_length=500, blank=True,
        help_text="Ex: Cameroun, Senegal, Cote d'Ivoire")

    ai_summary_fr = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    fetched_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["deadline", "-fetched_at"]
        verbose_name = "Bourse / Opportunite"
        verbose_name_plural = "Bourses / Opportunites"

    def __str__(self):
        return f"{self.title} — {self.provider}"

    @property
    def deadline_passed(self):
        if not self.deadline:
            return False
        from django.utils import timezone
        return self.deadline < timezone.now().date()


class UserOpportunityBookmark(models.Model):
    """Sauvegarde d'une offre ou d'une bourse par l'utilisateur."""
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="opportunity_bookmarks"
    )
    offer       = models.ForeignKey(
        AusbildungOffer, null=True, blank=True, on_delete=models.CASCADE,
        related_name="bookmarks"
    )
    scholarship = models.ForeignKey(
        ScholarshipOpportunity, null=True, blank=True, on_delete=models.CASCADE,
        related_name="bookmarks"
    )
    saved_at    = models.DateTimeField(auto_now_add=True)
    notes       = models.TextField(blank=True, help_text="Notes personnelles sur cette opportunite")
    applied     = models.BooleanField(default=False)
    applied_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-saved_at"]
        verbose_name = "Favori utilisateur"
        unique_together = [("user", "offer"), ("user", "scholarship")]

    def __str__(self):
        item = self.offer or self.scholarship
        return f"{self.user} → {item}"
