from django.db import models
from django.conf import settings

class CanadaCVProfile(models.Model):
    """
    Profil du candidat pour un CV au format canadien.
    Pas de photo, pas de date de naissance, pas de nationalité
    pour se conformer strictement aux normes anti-discrimination canadiennes.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="canada_cv_profile"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(
        max_length=300, blank=True,
        help_text="Ville, Pays actuel (ex: Douala, Cameroun)"
    )
    linkedin = models.URLField(blank=True, help_text="Lien vers votre profil LinkedIn")
    target_sector = models.CharField(
        max_length=100, blank=True,
        help_text="Secteur d'activité visé (ex: Informatique, Santé, Construction)"
    )
    target_provinces = models.CharField(
        max_length=300, blank=True,
        help_text="Provinces acceptées au Canada (ex: Québec, Ontario, Alberta)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil CV Canada"
        verbose_name_plural = "Profils CV Canada"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class CanadaCVExperience(models.Model):
    """Expérience professionnelle pour le CV canadien."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="canada_cv_experiences"
    )
    title = models.CharField(max_length=200, help_text="Ex: Développeur Python")
    company = models.CharField(max_length=200, help_text="Nom de l'employeur")
    city = models.CharField(max_length=100)
    province_country = models.CharField(max_length=100, default="Cameroun", help_text="Province ou Pays")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Laisser vide si en cours")
    is_current = models.BooleanField(default=False)
    description = models.TextField(
        blank=True,
        help_text="Responsabilités et réalisations clés. Utilisez des verbes d'action et chiffrez vos résultats."
    )
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Expérience Canada"
        verbose_name_plural = "Expériences Canada"

    def __str__(self):
        return f"{self.title} @ {self.company}"

    @property
    def period_display_fr(self):
        start = self.start_date.strftime("%m/%Y")
        if self.is_current or not self.end_date:
            return f"{start} – Présent"
        end = self.end_date.strftime("%m/%Y")
        return f"{start} – {end}"

    @property
    def period_display_en(self):
        start = self.start_date.strftime("%m/%Y")
        if self.is_current or not self.end_date:
            return f"{start} – Present"
        end = self.end_date.strftime("%m/%Y")
        return f"{start} – {end}"


class CanadaCVEducation(models.Model):
    """Diplôme ou formation pour le CV canadien."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="canada_cv_educations"
    )
    degree = models.CharField(max_length=200, help_text="Ex: Baccalauréat en génie logiciel (équivalent Licence)")
    school = models.CharField(max_length=200, help_text="Nom de l'établissement")
    city = models.CharField(max_length=100)
    province_country = models.CharField(max_length=100, default="Cameroun", help_text="Province ou Pays")
    start_year = models.IntegerField()
    end_year = models.IntegerField(null=True, blank=True, help_text="Laisser vide si en cours")
    description = models.TextField(blank=True, help_text="Détails optionnels sur le parcours académique")
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-start_year"]
        verbose_name = "Formation Canada"
        verbose_name_plural = "Formations Canada"

    def __str__(self):
        return f"{self.degree} — {self.school}"


class CanadaCVLanguage(models.Model):
    """Compétences linguistiques."""
    PROFICIENCY_CHOICES = [
        ("Maternelle", "Langue maternelle / Native"),
        ("Avancé", "Avancé (C1/C2)"),
        ("Intermédiaire", "Intermédiaire (B1/B2)"),
        ("Débutant", "Débutant (A1/A2)"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="canada_cv_languages"
    )
    language = models.CharField(max_length=50, help_text="Ex: Français, Anglais")
    proficiency = models.CharField(max_length=30, choices=PROFICIENCY_CHOICES)
    certificate = models.CharField(max_length=100, blank=True, help_text="Ex: TEF Canada CLB 9, IELTS 7.5")

    class Meta:
        ordering = ["language"]
        verbose_name = "Langue Canada"
        verbose_name_plural = "Langues Canada"

    def __str__(self):
        return f"{self.language} — {self.proficiency}"


class GeneratedCanadaResume(models.Model):
    """CV et lettre de motivation générés pour le Canada."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="canada_resumes_generated"
    )
    offer = models.ForeignKey(
        "jobs.CanadaJobOffer",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="canada_resumes"
    )
    custom_offer_title = models.CharField(max_length=300, blank=True)
    custom_offer_company = models.CharField(max_length=200, blank=True)
    
    language = models.CharField(
        max_length=5, 
        choices=[("fr", "Français"), ("en", "Anglais")], 
        default="fr"
    )
    
    content_html = models.TextField(help_text="Contenu HTML du CV généré")
    ai_cover_letter = models.TextField(blank=True, help_text="Lettre de motivation générée")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document Canada généré"
        verbose_name_plural = "Documents Canada générés"

    def __str__(self):
        target = self.offer or self.custom_offer_title or "Candidature libre"
        return f"CV Canada {self.user} → {target} ({self.get_language_display()})"

    @property
    def offer_title(self):
        if self.offer:
            return self.offer.title
        return self.custom_offer_title or "Candidature spontanée"


class CanadaImmigrationProfile(models.Model):
    """
    Profil d'immigration pour le calcul du score CRS Express Entry et diagnostic d'éligibilité.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="canada_immigration_profile"
    )
    age = models.IntegerField(default=25)
    education_level = models.CharField(
        max_length=50,
        choices=[
            ("doctorate", "Doctorat / Doctorate (PhD)"),
            ("master", "Maîtrise / Master's degree"),
            ("two_degrees", "Deux diplômes ou plus (dont un de 3 ans) / Two or more degrees"),
            ("bachelor", "Baccalauréat (3 ans et +) / Bachelor's degree (3+ years)"),
            ("two_year", "Diplôme de 2 ans / Two-year program"),
            ("one_year", "Diplôme de 1 an / One-year program"),
            ("high_school", "Études secondaires / High school"),
        ],
        default="bachelor"
    )
    work_experience_years = models.IntegerField(default=3)
    tcf_level = models.CharField(
        max_length=10,
        choices=[
            ("C2", "C2 (CLB 10+)"),
            ("C1", "C1 (CLB 9)"),
            ("B2", "B2 (CLB 7-8)"),
            ("B1", "B1 (CLB 5-6)"),
            ("A2", "A2 (CLB 4)"),
            ("A1", "A1 (CLB 1-3)"),
        ],
        default="B2"
    )
    has_lmia_job = models.BooleanField(default=False)
    crs_score = models.IntegerField(default=0)
    ai_roadmap = models.TextField(blank=True, help_text="Feuille de route générée par l'IA")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil d'immigration Canada"
        verbose_name_plural = "Profils d'immigration Canada"

    def __str__(self):
        return f"Diagnostic Canada {self.user} - Score: {self.crs_score}"

