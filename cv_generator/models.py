from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


# =====================================================
# CV TEMPLATE (STYLES & PAYWALL)
# =====================================================

class CVTemplate(models.Model):
    """
    Template de CV (HTML + style + paywall).
    NOTE: 'style' est important car certaines vues/JSON le demandent.
    """

    name = models.CharField(max_length=100, verbose_name="Nom du template")
    description = models.TextField(blank=True, verbose_name="Description")

    # Identifiant de style (ex: "canada_ats", "modern", "classic")
    style = models.CharField(
        max_length=60,
        default="canada_ats",
        help_text="Identifiant de style (ex: canada_ats, modern, classic)",
    )

    # Fichier template HTML associé
    template_file = models.CharField(
        max_length=200,
        default="cv_canada_ats.html",
        help_text="Nom du fichier template (ex: cv_canada_ats.html)",
    )

    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_premium = models.BooleanField(default=False, verbose_name="Premium")

    order = models.IntegerField(default=0, help_text="Ordre d'affichage (0 = premier)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Template de CV"
        verbose_name_plural = "Templates de CV"
        indexes = [
            models.Index(fields=["is_active", "is_premium", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.name}{' (Premium)' if self.is_premium else ''}"


# =====================================================
# CV (ENTITÉ CENTRALE)
# =====================================================

class CV(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cvs",
        db_index=True,
    )

    template = models.ForeignKey(
        CVTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cvs",
        verbose_name="Template",
    )

    # Infos perso
    prenom = models.CharField(max_length=100, blank=True, default="", verbose_name="Prénom")
    nom = models.CharField(max_length=100, blank=True, default="", verbose_name="Nom")
    titre_poste = models.CharField(max_length=200, blank=True, default="", verbose_name="Titre du poste")

    email = models.EmailField(blank=True, default="", verbose_name="Email")
    telephone = models.CharField(max_length=30, blank=True, default="", verbose_name="Téléphone")
    ville = models.CharField(max_length=100, blank=True, default="", verbose_name="Ville")
    province = models.CharField(max_length=100, blank=True, default="", verbose_name="Province")
    linkedin = models.URLField(blank=True, default="", verbose_name="LinkedIn")

    # Résumé
    resume_professionnel = models.TextField(
        blank=True,
        default="",
        verbose_name="Résumé professionnel (FR)",
        help_text="2-3 phrases décrivant votre profil",
    )
    summary = models.TextField(
        blank=True,
        default="",
        verbose_name="Résumé (EN)",
        help_text="Professional summary",
    )

    # Paramètres
    is_published = models.BooleanField(default=False, verbose_name="CV publié")
    pays_cible = models.CharField(max_length=100, blank=True, default="", verbose_name="Pays cible")
    language = models.CharField(max_length=10, blank=True, default="fr", verbose_name="Langue principale")
    profession = models.CharField(max_length=200, blank=True, default="", verbose_name="Profession/Secteur")

    # Progress wizard
    current_step = models.PositiveSmallIntegerField(default=1, verbose_name="Étape actuelle")
    is_completed = models.BooleanField(default=False, verbose_name="CV complété")

    step1_completed = models.BooleanField(default=False, verbose_name="Étape 1 complétée")
    step2_completed = models.BooleanField(default=False, verbose_name="Étape 2 complétée")
    step3_completed = models.BooleanField(default=False, verbose_name="Étape 3 complétée")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CV"
        verbose_name_plural = "CVs"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["is_completed", "is_published"]),
        ]

    def __str__(self) -> str:
        full = f"{self.prenom} {self.nom}".strip()
        return f"CV de {full or self.user}"


# =====================================================
# EXPERIENCE (CANONIQUE + ALIAS FR)
# =====================================================

class Experience(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="experiences", db_index=True)

    # Champs CANONIQUES (DB)
    title = models.CharField(max_length=200, blank=True, default="", verbose_name="Titre/Poste")
    company = models.CharField(max_length=200, blank=True, default="", verbose_name="Entreprise")
    location = models.CharField(max_length=200, blank=True, default="", verbose_name="Localisation")

    start_date = models.DateField(null=True, blank=True, verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")

    # Contenu
    description = models.TextField(blank=True, default="", verbose_name="Description")
    description_raw = models.TextField(blank=True, default="")
    description_ai = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Expérience"
        verbose_name_plural = "Expériences"
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["cv", "-start_date"]),
        ]

    def __str__(self) -> str:
        t = self.title.strip() or "Poste"
        c = self.company.strip() or "Entreprise"
        return f"{t} — {c}"

    # ===== ALIAS FR (pour tes templates / anciens accès) =====
    @property
    def poste(self) -> str:
        return self.title

    @poste.setter
    def poste(self, value: str) -> None:
        self.title = value or ""

    @property
    def entreprise(self) -> str:
        return self.company

    @entreprise.setter
    def entreprise(self, value: str) -> None:
        self.company = value or ""

    @property
    def ville(self) -> str:
        return self.location

    @ville.setter
    def ville(self, value: str) -> None:
        self.location = value or ""

    @property
    def date_debut(self) -> str:
        # Retour string YYYY-MM si possible (compat)
        return self.start_date.strftime("%Y-%m") if self.start_date else ""

    @property
    def date_fin(self) -> str:
        return self.end_date.strftime("%Y-%m") if self.end_date else ""


# =====================================================
# FORMATION/EDUCATION (CANONIQUE + ALIAS FR)
# =====================================================

class Formation(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="formations", db_index=True)

    # Canonique
    diploma = models.CharField(max_length=200, blank=True, default="", verbose_name="Diplôme")
    institution = models.CharField(max_length=200, blank=True, default="", verbose_name="Établissement")
    location = models.CharField(max_length=200, blank=True, default="", verbose_name="Localisation")

    start_date = models.DateField(null=True, blank=True, verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")

    # Optionnel (si tu veux afficher rapidement une année sans dates complètes)
    annee_obtention = models.CharField(max_length=10, blank=True, default="", verbose_name="Année (fallback)")

    description = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Formation"
        verbose_name_plural = "Formations"
        ordering = ["-end_date", "-created_at"]
        indexes = [
            models.Index(fields=["cv", "-end_date"]),
        ]

    def __str__(self) -> str:
        return self.diploma.strip() or "Formation"

    # ===== Alias FR =====
    @property
    def diplome(self) -> str:
        return self.diploma

    @diplome.setter
    def diplome(self, value: str) -> None:
        self.diploma = value or ""

    @property
    def etablissement(self) -> str:
        return self.institution

    @etablissement.setter
    def etablissement(self, value: str) -> None:
        self.institution = value or ""

    @property
    def ville(self) -> str:
        return self.location

    @ville.setter
    def ville(self, value: str) -> None:
        self.location = value or ""


# Alias compat
Education = Formation


# =====================================================
# COMPETENCE (LISTE SIMPLE)
# =====================================================

class Competence(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="competences", db_index=True)
    nom = models.CharField(max_length=200, verbose_name="Nom de la compétence")
    niveau = models.CharField(max_length=50, blank=True, default="", verbose_name="Niveau")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compétence"
        verbose_name_plural = "Compétences"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["cv", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.nom


# =====================================================
# SKILL (COMPÉTENCES CATÉGORISÉES) - OPTIONNEL
# =====================================================
# NOTE: garde-le si tu l'utilises vraiment.
# Sinon, on peut le supprimer plus tard et tout faire via Competence.
class Skill(models.Model):
    CATEGORY_CHOICES = [
        ("tech", "Technique"),
        ("soft", "Soft Skill"),
        ("lang", "Langue"),
        ("other", "Autre"),
    ]

    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="skills", db_index=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="tech")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "created_at"]
        indexes = [
            models.Index(fields=["cv", "category"]),
        ]

    def __str__(self) -> str:
        return self.name


# =====================================================
# LANGUE (CANONIQUE + ALIAS FR)
# =====================================================

class Langue(models.Model):
    NIVEAU_CHOICES = [
        ("Débutant", "Débutant"),
        ("Intermédiaire", "Intermédiaire"),
        ("Courant", "Courant"),
        ("Bilingue", "Bilingue"),
        ("Langue maternelle", "Langue maternelle"),
    ]

    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="langues", db_index=True)

    # Canonique
    name = models.CharField(max_length=100, blank=True, default="", verbose_name="Langue")
    level = models.CharField(max_length=50, blank=True, default="", verbose_name="Niveau")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Langue"
        verbose_name_plural = "Langues"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["cv", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.name.strip() or "Langue"

    # Alias FR
    @property
    def langue(self) -> str:
        return self.name

    @langue.setter
    def langue(self, value: str) -> None:
        self.name = value or ""

    @property
    def niveau(self) -> str:
        return self.level

    @niveau.setter
    def niveau(self, value: str) -> None:
        self.level = value or ""


Language = Langue


# =====================================================
# CERTIFICATION (CANONIQUE + ALIAS FR)
# =====================================================

class Certification(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="certifications", db_index=True)

    # Canonique
    name = models.CharField(max_length=200, blank=True, default="", verbose_name="Nom")
    organization = models.CharField(max_length=200, blank=True, default="", verbose_name="Organisme")

    date_obtained = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    credential_id = models.CharField(max_length=200, blank=True, default="")
    credential_url = models.URLField(blank=True, default="")

    # Fallback affichage rapide
    annee = models.CharField(max_length=10, blank=True, default="", verbose_name="Année (fallback)")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Certification"
        verbose_name_plural = "Certifications"
        ordering = ["-date_obtained", "-created_at"]
        indexes = [
            models.Index(fields=["cv", "-date_obtained"]),
        ]

    def __str__(self) -> str:
        return self.name.strip() or "Certification"

    # Alias FR
    @property
    def nom(self) -> str:
        return self.name

    @nom.setter
    def nom(self, value: str) -> None:
        self.name = value or ""

    @property
    def organisme(self) -> str:
        return self.organization

    @organisme.setter
    def organisme(self, value: str) -> None:
        self.organization = value or ""


# =====================================================
# VOLUNTEER
# =====================================================

class Volunteer(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="volunteers", db_index=True)
    role = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        indexes = [models.Index(fields=["cv", "-start_date"])]

    def __str__(self) -> str:
        return self.role


# =====================================================
# PROJECT
# =====================================================

class Project(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="projects", db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    technologies = models.CharField(max_length=255, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        indexes = [models.Index(fields=["cv", "-start_date"])]

    def __str__(self) -> str:
        return self.title


# =====================================================
# HOBBY
# =====================================================

class Hobby(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="hobbies", db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["cv", "created_at"])]

    def __str__(self) -> str:
        return self.name


# =====================================================
# CV UPLOAD (IMPORT CV)
# =====================================================

class CVUpload(models.Model):
    cv = models.OneToOneField(CV, on_delete=models.CASCADE, related_name="upload")
    file = models.FileField(upload_to="cv_uploads/")
    extracted_text = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[
            ("uploaded", "Uploaded"),
            ("parsed", "Parsed"),
            ("error", "Error"),
        ],
        default="uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Upload CV #{self.cv_id}"


# =====================================================
# HISTORIQUE DES VERSIONS
# =====================================================

class CVVersion(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="versions", db_index=True)
    snapshot = models.JSONField(help_text="Snapshot complet du CV à un instant T")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["cv", "-created_at"])]

    def __str__(self) -> str:
        return f"Version CV #{self.cv_id} — {self.created_at:%d/%m/%Y %H:%M}"
