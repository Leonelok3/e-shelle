from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# ----------- Catalogue d'examens -----------

class Exam(models.Model):
    """
    Représente un examen (TCF, TEF, IELTS, CELPIP, Goethe, TestDaF).
    """
    code = models.SlugField(
        unique=True,
        help_text=_("Code court: tcf, tef, ielts, celpip, goethe, testdaf")
    )
    name = models.CharField(max_length=100)
    language = models.CharField(
        max_length=2,
        choices=[("fr", "Français"), ("en", "Anglais"), ("de", "Allemand")],
        help_text=_("Langue principale de l'examen"),
    )
    description = models.TextField(blank=True, null=True)


    class Meta:
        verbose_name = _("Examen")
        verbose_name_plural = _("Examens")

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ExamSection(models.Model):
    """
    Section d'un examen (listening/reading/writing/speaking) avec durée.
    Exemple : TEF CO / CE / EE / EO, TCF CO / CE / EE / EO, etc.
    """
    class SectionCode(models.TextChoices):
        LISTENING = "listening", _("Compréhension orale")
        READING = "reading", _("Compréhension écrite")
        WRITING = "writing", _("Expression écrite")
        SPEAKING = "speaking", _("Expression orale")

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="sections"
    )
    code = models.CharField(max_length=20, choices=SectionCode.choices)
    order = models.PositiveIntegerField(default=1)
    duration_sec = models.PositiveIntegerField(
        default=600,
        help_text=_("Durée en secondes")
    )

    class Meta:
        verbose_name = _("Section d'examen")
        verbose_name_plural = _("Sections d'examen")
        ordering = ["exam", "order"]

    def __str__(self) -> str:
        return f"{self.exam.code}:{self.code}"


# ----------- Banque de contenus -----------

class Passage(models.Model):
    """
    Texte support pour questions de lecture/écoute (transcription).
    """
    title = models.CharField(max_length=200, blank=True)
    text = models.TextField()

    class Meta:
        verbose_name = _("Passage")
        verbose_name_plural = _("Passages")

    def __str__(self) -> str:
        return self.title or f"Passage #{self.pk}"


class Asset(models.Model):
    """
    Ressource média (audio/vidéo/image/pdf) — MVP : URL externe.
    """
    KIND_CHOICES = [
        ("audio", "Audio"),
        ("video", "Vidéo"),
        ("image", "Image"),
        ("pdf", "PDF"),
    ]
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    url = models.URLField(help_text=_("URL du fichier média"))
    lang = models.CharField(
        max_length=2,
        choices=[("fr", "Français"), ("en", "Anglais"), ("de", "Allemand")],
        default="fr",
    )

    class Meta:
        verbose_name = _("Média")
        verbose_name_plural = _("Médias")

    def __str__(self) -> str:
        return f"{self.kind}:{self.url}"


class Question(models.Model):
    """
    Question générique.
    - subtype: 'mcq' (choix unique), 'short' (réponse texte court)
    - passage ou asset en option (selon le type)
    """
    SUBTYPE_CHOICES = [
        ("mcq", "QCM (choix unique)"),
        ("short", "Texte court"),
    ]
    section = models.ForeignKey(
        ExamSection,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    subtype = models.CharField(
        max_length=10,
        choices=SUBTYPE_CHOICES,
        default="mcq"
    )
    stem = models.TextField(help_text=_("Énoncé de la question"))
    passage = models.ForeignKey(
        Passage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions"
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions"
    )
    difficulty = models.FloatField(
        default=0.5,
        help_text=_("0=très facile, 1=très difficile (indicatif)")
    )

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self) -> str:
        return f"Q#{self.pk} [{self.section.exam.code}/{self.section.code}]"

    @property
    def audio_url(self):
        """Retourne l'URL audio si un asset audio est lié, sinon None."""
        if self.asset and self.asset.kind == "audio" and self.asset.url:
            return self.asset.url
        return None


class Choice(models.Model):
    """
    Choix de réponse pour QCM (mcq).
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices"
    )
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Choix")
        verbose_name_plural = _("Choix")

    def __str__(self) -> str:
        return f"Choix Q{self.question_id}: {self.text[:40]}"


class Explanation(models.Model):
    """
    Explication/feedback relié à une question (utile pour corrections détaillées).
    """
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        related_name="explanation"
    )
    text_md = models.TextField(help_text=_("Explication en Markdown"))

    class Meta:
        verbose_name = _("Explication")
        verbose_name_plural = _("Explications")

    def __str__(self) -> str:
        return f"Explication Q{self.question_id}"


# ----------- Exécution & réponses -----------

class Session(models.Model):
    """
    Session d'entraînement (mock ou practice). MVP: pratique simple.
    """
    MODE_CHOICES = [
        ("practice", "Entraînement"),
        ("mock", "Examen blanc"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="prep_sessions"
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="sessions"
    )
    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default="practice"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Session")
        verbose_name_plural = _("Sessions")

    def __str__(self) -> str:
        return f"Session {self.user_id} - {self.exam.code} ({self.mode})"


class Attempt(models.Model):
    """
    Tentative par section dans une session.
    """
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    section = models.ForeignKey(
        ExamSection,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    elapsed_sec = models.PositiveIntegerField(default=0)
    raw_score = models.FloatField(default=0.0)      # score brut (nb de bonnes réponses)
    total_items = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("Tentative")
        verbose_name_plural = _("Tentatives")
        unique_together = ("session", "section")

    def __str__(self) -> str:
        return f"Attempt S{self.session_id}-{self.section.code}"


class Answer(models.Model):
    """
    Réponse utilisateur à une question.
    - Pour QCM: payload = {"choice_id": X}
    - Pour short: payload = {"text": "..."}

    Les réponses sont liées à une tentative (Attempt) et une question (Question).
    """
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    payload = models.JSONField(default=dict)
    is_correct = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Réponse")
        verbose_name_plural = _("Réponses")
        unique_together = ("attempt", "question")

    def __str__(self) -> str:
        return f"Answer A{self.attempt_id}-Q{self.question_id}"


# ----------- CMS Cours TEF / TCF (mini) -----------

class CourseLesson(models.Model):
    """
    Leçons de cours spécifiques à une section d'examen.
    Tu pourras créer :
      - exam = TEF, section = "eo", "ee", "co", "ce"
      - exam = TCF, section = "eo", "ee", "co", "ce"
    directement depuis l’admin.
    """
    SECTION_CHOICES = [
        ("co", "Compréhension orale"),
        ("ce", "Compréhension écrite"),
        ("ee", "Expression écrite"),
        ("eo", "Expression orale"),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="course_lessons"
    )  # ex: TEF / TCF
    section = models.CharField(
        max_length=2,
        choices=SECTION_CHOICES
    )  # co/ce/ee/eo

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)

    # langue de la leçon (tu peux plus tard traduire)
    locale = models.CharField(
        max_length=2,
        default="fr",
        choices=[("fr", "Français"), ("en", "English"), ("de", "Deutsch")],
    )

    # Contenu HTML (tu peux coller du HTML/embeds simples : <p>, <ul>, <strong>, <em>, <audio>, <iframe>…)
    content_html = models.TextField(
        help_text=_("HTML autorisé : paragraphes, listes, titres, audio, iframe.")
    )

    order = models.PositiveIntegerField(
        default=1,
        help_text=_("Ordre d’affichage (1=haut).")
    )
    is_published = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Leçon de cours")
        verbose_name_plural = _("Leçons de cours")
        ordering = ["exam", "section", "order", "id"]
        unique_together = (("exam", "section", "slug", "locale"),)

    def __str__(self) -> str:
        return f"{self.exam.code.upper()} {self.section.upper()} — {self.title} ({self.locale})"


# ----------- Exercices de cours (QCM + questions ouvertes) -----------

class CourseExercise(models.Model):
    """
    Exercice rattaché à une leçon de cours :
    - texte (consigne + question)
    - médias (audio/image)
    - QCM (A/B/C/D) OU question ouverte
    - résumé / correction
    Tu les créeras aussi depuis l’admin, rattachés à une CourseLesson.
    """
    lesson = models.ForeignKey(
        CourseLesson,
        on_delete=models.CASCADE,
        related_name="exercises",
        verbose_name=_("Leçon")
    )

    title = models.CharField(_("Titre de l'exercice"), max_length=200)

    instruction = models.TextField(
        _("Consigne"),
        blank=True,
        help_text=_("Ce que l'apprenant doit faire.")
    )

    question_text = models.TextField(
        _("Texte / question"),
        help_text=_("Texte de la question, dialogue, énoncé…")
    )

    # --- Options QCM (facultatives : si vides -> question ouverte) ---
    option_a = models.CharField(_("Option A"), max_length=255, blank=True)
    option_b = models.CharField(_("Option B"), max_length=255, blank=True)
    option_c = models.CharField(_("Option C"), max_length=255, blank=True)
    option_d = models.CharField(_("Option D"), max_length=255, blank=True)

    correct_option = models.CharField(
        _("Bonne réponse"),
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        blank=True,
        help_text=_("Lettre de la bonne réponse (A, B, C, D). Laisser vide pour une question ouverte.")
    )

    # Médias locaux (pour tes cours / activités)
    audio = models.FileField(
        _("Fichier audio"),
        upload_to="course_exercises/audio/",
        blank=True,
        null=True,
    )

    image = models.ImageField(
        _("Image"),
        upload_to="course_exercises/images/",
        blank=True,
        null=True,
    )

    # Optionnel : texte support générique
    passage = models.ForeignKey(
        Passage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_exercises",
        verbose_name=_("Passage lié"),
        help_text=_("Texte support si nécessaire.")
    )

    # Résumé / correction détaillée
    summary = models.TextField(
        _("Résumé / correction"),
        blank=True,
        help_text=_("Explication affichée après l'exercice.")
    )

    order = models.PositiveIntegerField(
        default=1,
        help_text=_("Ordre d’affichage dans la leçon (1=haut).")
    )
    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Exercice de cours")
        verbose_name_plural = _("Exercices de cours")
        ordering = ["lesson", "order", "id"]

    def __str__(self):
        return f"{self.lesson.title} — {self.title}"

    @property
    def is_mcq(self) -> bool:
        """
        Retourne True si l'exercice est un QCM
        (au moins une option + une bonne réponse).
        """
        has_options = any([self.option_a, self.option_b, self.option_c, self.option_d])
        return bool(has_options and self.correct_option)
        # NB : Tu ajouteras les cours + exercices EO/EE directement depuis l’admin.
