from django.db import models
from django.conf import settings


# =====================================================
# CV TEMPLATE (STYLES & PAYWALL)
# =====================================================
class CVTemplate(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    style = models.CharField(
        max_length=50,
        help_text="Identifiant technique du template (ex: canada, europe, modern)"
    )

    is_active = models.BooleanField(default=True)

    # 💰 PAYWALL
    is_premium = models.BooleanField(
        default=False,
        help_text="Template réservé aux comptes Premium"
    )

    def __str__(self):
        return self.name


# =====================================================
# CV (ENTITÉ CENTRALE)
# =====================================================
class CV(models.Model):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cvs"
    )

    template = models.ForeignKey(
        CVTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cvs"
    )

    profession = models.CharField(max_length=255, blank=True)
    pays_cible = models.CharField(max_length=100, blank=True)

    summary = models.TextField(blank=True)

    # Données libres (upload, parsing, préférences…)
    data = models.JSONField(default=dict, blank=True)

    language = models.CharField(
        max_length=2,
        choices=[("fr", "Français"), ("en", "English")],
        default="fr"
    )

    # === PROGRESSION PAR ÉTAPES ===
    current_step = models.PositiveSmallIntegerField(default=1)

    step1_completed = models.BooleanField(default=False)
    step2_completed = models.BooleanField(default=False)
    step3_completed = models.BooleanField(default=False)

    is_completed = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    # =============================
    # MÉTHODES UTILITAIRES
    # =============================
    def get_completion_percentage(self):
        steps = [
            self.step1_completed,
            self.step2_completed,
            self.step3_completed,
        ]
        return int((sum(1 for s in steps if s) / len(steps)) * 100)

    def __str__(self):
        return f"CV #{self.id} — {self.profession or 'Sans titre'}"


# =====================================================
# EXPERIENCE
# =====================================================
class Experience(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="experiences"
    )

    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    description_raw = models.TextField(blank=True)
    description_ai = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} — {self.company}"


# =====================================================
# EDUCATION
# =====================================================
class Education(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="educations"
    )

    diploma = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True)

    def __str__(self):
        return self.diploma


# =====================================================
# SKILL
# =====================================================
class Skill(models.Model):
    CATEGORY_CHOICES = [
        ("tech", "Technique"),
        ("soft", "Soft Skill"),
        ("lang", "Langue"),
        ("other", "Autre"),
    ]

    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="skills"
    )

    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="tech"
    )

    def __str__(self):
        return self.name


# =====================================================
# LANGUAGE
# =====================================================
class Language(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="languages"
    )

    name = models.CharField(max_length=100)
    level = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.level})"


# =====================================================
# VOLUNTEER
# =====================================================
class Volunteer(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="volunteers"
    )

    role = models.CharField(max_length=200)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True)

    def __str__(self):
        return self.role


# =====================================================
# CERTIFICATION
# =====================================================
class Certification(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="certifications"
    )

    name = models.CharField(max_length=200)
    organization = models.CharField(max_length=200)

    date_obtained = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    credential_id = models.CharField(max_length=200, blank=True)
    credential_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


# =====================================================
# PROJECT
# =====================================================
class Project(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="projects"
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    technologies = models.CharField(max_length=255, blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    url = models.URLField(blank=True)

    def __str__(self):
        return self.title


# =====================================================
# HOBBY
# =====================================================
class Hobby(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="hobbies"
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# =====================================================
# CV UPLOAD (IMPORT CV)
# =====================================================
class CVUpload(models.Model):
    cv = models.OneToOneField(
        CV,
        on_delete=models.CASCADE,
        related_name="upload"
    )

    file = models.FileField(upload_to="cv_uploads/")
    extracted_text = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("uploaded", "Uploaded"),
            ("parsed", "Parsed"),
            ("error", "Error"),
        ],
        default="uploaded"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload CV #{self.cv.id}"


# =====================================================
# 🕒 HISTORIQUE DES VERSIONS (PRO)
# =====================================================
class CVVersion(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="versions"
    )

    snapshot = models.JSONField(
        help_text="Snapshot complet du CV à un instant T"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Version CV #{self.cv.id} — {self.created_at:%d/%m/%Y %H:%M}"


