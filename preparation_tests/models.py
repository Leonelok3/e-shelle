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

# =====================================================
# 📊 PROGRESSION & CERTIFICATS
# =====================================================

class UserSkillProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exam_code = models.CharField(max_length=20)
    skill = models.CharField(max_length=2)
    score_percent = models.PositiveIntegerField(default=0)


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
