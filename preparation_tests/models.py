from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from core.constants import LEVEL_CHOICES, LEVEL_ORDER

# =====================================================
# 📘 EXAMENS
# =====================================================

class Exam(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    language = models.CharField(
        max_length=2,
        choices=[("fr", "Français"), ("en", "Anglais"), ("de", "Allemand")],
    )
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ExamSection(models.Model):
    class SectionCode(models.TextChoices):
        CO = "co", _("Compréhension orale")
        CE = "ce", _("Compréhension écrite")
        EE = "ee", _("Expression écrite")
        EO = "eo", _("Expression orale")

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="sections")
    code = models.CharField(max_length=2, choices=SectionCode.choices)
    order = models.PositiveIntegerField(default=1)
    duration_sec = models.PositiveIntegerField(default=600)

    def __str__(self):
        return f"{self.exam.code.upper()} - {self.code.upper()}"


# =====================================================
# 📚 CONTENU
# =====================================================

class Passage(models.Model):
    title = models.CharField(max_length=200, blank=True)
    text = models.TextField()

    def __str__(self):
        return self.title or f"Passage {self.pk}"


class Asset(models.Model):
    kind = models.CharField(
        max_length=20,
        choices=[("audio", "Audio"), ("image", "Image"), ("video", "Video")],
    )
    file = models.FileField(upload_to="assets/")
    lang = models.CharField(max_length=10, default="fr")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} ({self.lang})"

    @property
    def public_url(self) -> str:
        """
        URL classique (non protégée) servie par MEDIA_URL.
        Ne casse rien : c'est le comportement actuel.
        """
        try:
            return self.file.url
        except Exception:
            return ""

    @property
    def secure_url(self) -> str:
        """
        URL protégée : passe par /protected-media/...
        Compatible avec notre endpoint mediafiles (dev/prod-ready).
        """
        if not self.file:
            return ""

        # file.name ressemble à "assets/xxx.mp3"
        # On veut /protected-media/assets/xxx.mp3
        return f"{settings.PROTECTED_MEDIA_URL}{self.file.name}"



# =====================================================
# 📝 QUESTIONS
# =====================================================

class Question(models.Model):
    SUBTYPE_CHOICES = [
        ("mcq", "Choix multiple"),
        ("text", "Texte libre"),
        ("audio", "Audio"),
    ]

    DIFFICULTY_CHOICES = [
        ("easy", "Facile"),
        ("medium", "Moyen"),
        ("hard", "Difficile"),
    ]

    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name="questions")
    stem = models.TextField()
    passage = models.ForeignKey(Passage, null=True, blank=True, on_delete=models.SET_NULL)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.SET_NULL)
    subtype = models.CharField(max_length=10, choices=SUBTYPE_CHOICES, default="mcq")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")

    def __str__(self):
        return f"Question {self.pk}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)


class Explanation(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE)
    text_md = models.TextField()


# =====================================================
# ⏱️ SESSIONS
# =====================================================

class Session(models.Model):
    MODE_CHOICES = [
        ("practice", "Entraînement"),
        ("mock", "Examen blanc"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_sessions")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    section = models.ForeignKey(
        ExamSection,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sessions"
    )

    mode = models.CharField(max_length=10, choices=MODE_CHOICES)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    total_score = models.FloatField(default=0)
    duration_sec = models.PositiveIntegerField(default=0)


class Attempt(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attempts")
    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE)

    raw_score = models.PositiveIntegerField(default=0)
    total_items = models.PositiveIntegerField(default=0)

    score_percent = models.FloatField(default=0)



class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    payload = models.JSONField(default=dict)


# =====================================================
# 📖 COURS (TOUS ACCESSIBLES)
# =====================================================

from django.db import models

class CourseLesson(models.Model):
    """
    📘 Leçon CECR universelle (TRANSITION)
    """

    # 🔒 ANCIEN LIEN (NE PAS SUPPRIMER MAINTENANT)
    exam = models.ForeignKey(
        "preparation_tests.Exam",
        on_delete=models.CASCADE,
        related_name="legacy_lessons",
        null=True,
        blank=True,
    )

    # 🆕 NOUVEAU LIEN MULTI-EXAMENS (PRO)
    exams = models.ManyToManyField(
        "preparation_tests.Exam",
        related_name="lessons",
        blank=True,
        help_text="Examens utilisant cette leçon (TEF, TCF, DELF, DALF)",
    )

    section = models.CharField(
        max_length=2,
        choices=[
            ("co", "Compréhension Orale"),
            ("ce", "Compréhension Écrite"),
            ("ee", "Expression Écrite"),
            ("eo", "Expression Orale"),
        ],
    )

    level = models.CharField(
        max_length=2,
        choices=[
            ("A1", "A1"),
            ("A2", "A2"),
            ("B1", "B1"),
            ("B2", "B2"),
            ("C1", "C1"),
            ("C2", "C2"),
        ],
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    locale = models.CharField(max_length=5, default="fr")

    content_html = models.TextField()

    order = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["level", "order"]
        verbose_name = "Leçon"
        verbose_name_plural = "Leçons"

    def __str__(self):
        exams = ", ".join(e.code.upper() for e in self.exams.all())
        return f"[{self.level}] {self.section.upper()} – {self.title} ({exams})"

    @property
    def cefr_level(self):
        return self.level

    def is_accessible_by(self, user):
        return True


###############################################################################

class CourseExercise(models.Model):
    lesson = models.ForeignKey(
        CourseLesson,
        on_delete=models.CASCADE,
        related_name="exercises",
    )

    title = models.CharField(max_length=255)
    instruction = models.TextField(blank=True)
    question_text = models.TextField()

    audio = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exercise_audios",
    )

    image = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exercise_images",
    )

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)

    correct_option = models.CharField(
        max_length=1,
        choices=[
            ("A", "A"),
            ("B", "B"),
            ("C", "C"),
            ("D", "D"),
        ],
    )

    summary = models.TextField(blank=True)

    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.lesson.title} – Exercice {self.order}"

    @property
    def audio_url(self) -> str:
        """
        URL audio publique — servie via /media/ par Django (dev) ou Nginx (prod).
        La protection premium est gérée au niveau du template (row.can_audio).
        """
        if not self.audio or self.audio.kind != "audio":
            return ""
        return self.audio.public_url

    @property
    def audio_public_url(self) -> str:
        """
        URL audio publique (legacy) si tu as besoin de comparer.
        """
        if not self.audio or self.audio.kind != "audio":
            return ""
        return self.audio.public_url


# =====================================================
# 📊 PROGRESSION & CERTIFICATS
# =====================================================

class UserSkillProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exam_code = models.CharField(max_length=20)
    skill = models.CharField(max_length=2)
    score_percent = models.PositiveIntegerField(default=0)
    # Niveau CECR courant (A1..C2)
    current_level = models.CharField(
        max_length=2,
        choices=LEVEL_CHOICES,
        default="A1",
    )
    # Nombre total de tentatives prises en compte
    total_attempts = models.PositiveIntegerField(default=0)


class UserSkillResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    section = models.ForeignKey(
        ExamSection,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    score_percent = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()

class UserLessonProgress(models.Model):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )

    lesson = models.ForeignKey(
        CourseLesson,
        on_delete=models.CASCADE,
        related_name="user_progress",
    )

    percent = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_exercises = models.PositiveIntegerField(default=0)
    total_exercises = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

class CEFRCertificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exam_code = models.CharField(max_length=20)
    level = models.CharField(max_length=2)

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    issued_at = models.DateTimeField(auto_now_add=True)

# =====================================================
# 🗺️ PLAN D'ÉTUDE
# =====================================================

class StudyPlanProgress(models.Model):
    """
    Suivi du plan d'étude personnalisé de l'utilisateur
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exam_code = models.CharField(max_length=20)
    current_day = models.PositiveIntegerField(default=1)
    total_days = models.PositiveIntegerField(default=30)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ["user", "exam_code"]
        ordering = ["-last_activity"]

    def __str__(self):
        return f"{self.user.username} - {self.exam_code} (Jour {self.current_day}/{self.total_days})"


class CoachIAReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coach_reports",
    )

    exam_code = models.CharField(max_length=20)
    scope = models.CharField(
        max_length=20,
        choices=[
            ("global", "Global"),
            ("co", "Compréhension orale"),
            ("ce", "Compréhension écrite"),
            ("ee", "Expression écrite"),
            ("eo", "Expression orale"),
        ],
        default="global",
    )

    data = models.JSONField()  # analyse IA complète
    score_snapshot = models.JSONField(default=dict)  # scores au moment T

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"IA {self.exam_code} ({self.scope}) – {self.created_at:%Y-%m-%d}"


from django.db import models
from django.conf import settings
from django.utils import timezone


class UserExerciseProgress(models.Model):
    """
    1 ligne par (user, exercise).
    Permet d’éviter le double comptage et d’avoir une progression fiable.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey("preparation_tests.CourseLesson", on_delete=models.CASCADE)
    exercise = models.ForeignKey("preparation_tests.CourseExercise", on_delete=models.CASCADE)

    is_completed = models.BooleanField(default=False)  # completed = réponse correcte validée
    attempts = models.PositiveIntegerField(default=0)
    last_answer = models.CharField(max_length=1, blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "exercise")
        indexes = [
            models.Index(fields=["user", "lesson"]),
            models.Index(fields=["user", "exercise"]),
        ]

    def mark_attempt(self, selected: str, correct: bool):
        self.attempts = (self.attempts or 0) + 1
        self.last_answer = (selected or "").upper()

        if correct and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()


# =====================================================
# 🎤 SOUMISSIONS EO / EE
# =====================================================

class EOSubmission(models.Model):
    """
    Enregistrement audio soumis par un étudiant pour un exercice EO.
    L'IA transcrit (Whisper) puis évalue la prise de parole.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="eo_submissions")
    exercise = models.ForeignKey("preparation_tests.CourseExercise", on_delete=models.CASCADE, related_name="eo_submissions")
    audio_file = models.FileField(upload_to="eo_submissions/", blank=True)
    transcript = models.TextField(blank=True)
    score = models.FloatField(null=True, blank=True)  # 0–100
    feedback_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"EO #{self.pk} — {self.user} — {self.score}/100"


class EESubmission(models.Model):
    """
    Texte rédigé par un étudiant pour un exercice EE.
    L'IA corrige la production écrite et la note.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ee_submissions")
    exercise = models.ForeignKey("preparation_tests.CourseExercise", on_delete=models.CASCADE, related_name="ee_submissions")
    text = models.TextField()
    word_count = models.PositiveIntegerField(default=0)
    score = models.FloatField(null=True, blank=True)  # 0–100
    feedback_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"EE #{self.pk} — {self.user} — {self.score}/100"



# =====================================================
# 🧪 HISTORIQUE EXAMENS BLANCS PAR NIVEAU CECR
# =====================================================

class MockExamResult(models.Model):
    """
    Enregistre le résultat d'un examen blanc par niveau CECR.
    Un enregistrement par passage (POST de level_mock_exam).
    """
    LEVEL_CHOICES = [
        ("A1", "A1"), ("A2", "A2"),
        ("B1", "B1"), ("B2", "B2"),
        ("C1", "C1"), ("C2", "C2"),
    ]

    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mock_exam_results",
    )
    level         = models.CharField(max_length=2, choices=LEVEL_CHOICES, db_index=True)
    score_co      = models.PositiveIntegerField(null=True, blank=True)
    score_ce      = models.PositiveIntegerField(null=True, blank=True)
    score_global  = models.PositiveIntegerField(null=True, blank=True)
    co_correct    = models.PositiveIntegerField(default=0)
    co_total      = models.PositiveIntegerField(default=0)
    ce_correct    = models.PositiveIntegerField(default=0)
    ce_total      = models.PositiveIntegerField(default=0)
    cefr_estimate = models.CharField(max_length=10, blank=True)
    taken_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_at"]
        verbose_name = "Résultat examen blanc"
        verbose_name_plural = "Résultats examens blancs"

    def __str__(self):
        return f"{self.user} — {self.level} — {self.score_global}% ({self.taken_at:%Y-%m-%d})"
