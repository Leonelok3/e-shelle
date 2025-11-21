from django.conf import settings
from django.db import models


class PRProfile(models.Model):
    # --------- CHOIX --------- #
    COUNTRY_CHOICES = [
        ("CA", "Canada"),
        ("AU", "Australie"),
    ]

    EDUCATION_CHOICES = [
        ("secondary", "Secondaire / Bac"),
        ("post_1_2", "Post-secondaire 1–2 ans (BTS, DUT, etc.)"),
        ("bachelor", "Licence / Bachelor"),
        ("master", "Master"),
        ("phd", "Doctorat / PhD"),
        ("other", "Autre / mixte"),
    ]

    FRENCH_EXAM_CHOICES = [
        ("none", "Aucun test pour l’instant"),
        ("tef_canada", "TEF Canada"),
        ("tcf_canada", "TCF Canada"),
        ("tefaq", "TEFAQ"),
        ("tcf_other", "TCF / DELF / DALF (autre)"),
    ]

    ENGLISH_EXAM_CHOICES = [
        ("none", "Aucun test pour l’instant"),
        ("ielts_general", "IELTS General Training"),
        ("celpip_general", "CELPIP General"),
        ("pte_core", "PTE Core"),
        ("toefl", "TOEFL iBT (info)"),
    ]

    LANGUAGE_LEVEL_CHOICES = [
        ("none", "Pas encore de niveau ou test"),
        ("a2", "A1–A2 (débutant)"),
        ("b1", "B1 (intermédiaire)"),
        ("b2", "B2 (intermédiaire avancé)"),
        ("c1", "C1 (avancé)"),
        ("c2", "C2 (très avancé)"),
    ]

    # --------- PROFIL GÉNÉRAL --------- #
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pr_profiles",
    )

    country = models.CharField(
        max_length=2,
        choices=COUNTRY_CHOICES,
        default="CA",
    )

    age = models.PositiveIntegerField(null=True, blank=True)
    years_experience = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Années d'expérience qualifiée à temps plein.",
    )

    education_level = models.CharField(
        max_length=20,
        choices=EDUCATION_CHOICES,
        blank=True,
    )

    # --------- FRANÇAIS --------- #
    french_exam = models.CharField(
        "Test de français",
        max_length=30,
        choices=FRENCH_EXAM_CHOICES,
        default="none",
    )
    french_level = models.CharField(
        "Niveau global de français",
        max_length=10,
        choices=LANGUAGE_LEVEL_CHOICES,
        default="none",
    )

    # Sous-scores FR (CO / CE / EO / EE)
    french_co = models.CharField(
        "Français – Compréhension orale (CO)",
        max_length=20,
        blank=True,
        help_text="Ex : 310/360, CLB 7, B2 …",
    )
    french_ce = models.CharField(
        "Français – Compréhension écrite (CE)",
        max_length=20,
        blank=True,
        help_text="Ex : 280/300, CLB 8, B2 …",
    )
    french_eo = models.CharField(
        "Français – Expression orale (EO)",
        max_length=20,
        blank=True,
    )
    french_ee = models.CharField(
        "Français – Expression écrite (EE)",
        max_length=20,
        blank=True,
    )

    # --------- ANGLAIS --------- #
    english_exam = models.CharField(
        "Test d’anglais",
        max_length=30,
        choices=ENGLISH_EXAM_CHOICES,
        default="none",
    )
    english_level = models.CharField(
        "Niveau global d’anglais",
        max_length=10,
        choices=LANGUAGE_LEVEL_CHOICES,
        default="none",
    )

    # Sous-scores EN (CO / CE / EO / EE)
    english_co = models.CharField(
        "Anglais – Compréhension orale (Listening)",
        max_length=20,
        blank=True,
        help_text="Ex : 6.5, 7.0, CLB 8 …",
    )
    english_ce = models.CharField(
        "Anglais – Compréhension écrite (Reading)",
        max_length=20,
        blank=True,
    )
    english_eo = models.CharField(
        "Anglais – Expression orale (Speaking)",
        max_length=20,
        blank=True,
    )
    english_ee = models.CharField(
        "Anglais – Expression écrite (Writing)",
        max_length=20,
        blank=True,
    )

    # --------- AUTRES --------- #
    profession_title = models.CharField(
        max_length=200,
        blank=True,
    )
    noc_code = models.CharField(
        max_length=20,
        blank=True,
    )
    anzsco_code = models.CharField(
        max_length=20,
        blank=True,
    )

    has_family_in_country = models.BooleanField(default=False)
    has_job_offer = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Profil RP #{self.pk} – {self.user}"



class PRPlanStep(models.Model):
    STATUS_CHOICES = [
        ("todo", "À faire"),
        ("in_progress", "En cours"),
        ("done", "Terminé"),
    ]

    profile = models.ForeignKey(
        PRProfile,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="todo",
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.profile} · {self.order} · {self.title}"

    @property
    def category(self) -> str:
        """
        Catégorie logique (non stockée en base) utilisée pour filtrer
        dans le plan RP. On se base sur le texte de l'étape.
        """
        t = (self.title or "").lower()

        if "langue" in t or "ielts" in t or "tef" in t or "tcf" in t or "pte" in t:
            return "languages"
        if "diplôme" in t or "ede" in t or "document" in t or "skills assessment" in t:
            return "documents"
        if "canada" in t or "entrée express" in t or "pnp" in t or "arrima" in t:
            return "canada"
        if "australie" in t or "skilled" in t or "sponsor" in t:
            return "australia"

        return "all"


# --- Programmes d'immigration & ressources associées ---

class ImmigrationProgram(models.Model):
    COUNTRY_CHOICES = [
        ("CA", "Canada"),
        ("AU", "Australie"),
    ]

    slug = models.SlugField(
        unique=True,
        help_text="Identifiant dans l’URL, ex: 'entree-express' ou 'nsw-skilled-visa'.",
    )
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    category = models.CharField(
        max_length=80,
        blank=True,
        help_text="Ex: Entrée Express, PNP, Visa Skilled, State Nomination…",
    )
    short_label = models.CharField(
        max_length=80,
        blank=True,
        help_text="Label court pour les badges, ex: 'Entrée Express – FSW'.",
    )
    summary = models.TextField(
        blank=True,
        help_text="Résumé rapide du programme (objectif, profil ciblé).",
    )
    official_url = models.URLField(
        blank=True,
        help_text="Lien officiel vers le site du gouvernement.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["country", "name"]
        verbose_name = "Programme d'immigration"
        verbose_name_plural = "Programmes d'immigration"

    def __str__(self) -> str:  # type: ignore[override]
        return f"{self.name} ({self.get_country_display()})"


class ProgramResource(models.Model):
    TYPE_CHOICES = [
        ("OFFICIAL", "Lien officiel"),
        ("VIDEO", "Vidéo"),
        ("SCREENSHOT", "Capture d’écran"),
        ("DOC", "Document / PDF"),
        ("CHECKLIST", "Checklist"),
        ("ARTICLE", "Article / Guide"),
        ("OTHER", "Autre"),
    ]

    program = models.ForeignKey(
        ImmigrationProgram,
        related_name="resources",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=200)
    resource_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="ARTICLE",
    )
    description = models.TextField(blank=True)

    # URL vers la vidéo, article, page externe, PDF, etc.
    url = models.URLField(blank=True)

    # Pour stocker une capture d’écran ou visuel de la ressource
    image = models.ImageField(
        upload_to="rp_resources/screenshots/",
        blank=True,
        null=True,
    )

    # Pour Youtube/Vimeo si tu veux intégrer un <iframe> plus tard
    embed_code = models.TextField(
        blank=True,
        help_text="Optionnel: code d’intégration (iframe) pour une vidéo.",
    )

    order = models.PositiveIntegerField(
        default=0,
        help_text="Permet de trier l’ordre d’affichage des ressources.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["resource_type", "order", "id"]
        verbose_name = "Ressource programme RP"
        verbose_name_plural = "Ressources programme RP"

    def __str__(self) -> str:  # type: ignore[override]
        return f"{self.title} ({self.get_resource_type_display()})"
