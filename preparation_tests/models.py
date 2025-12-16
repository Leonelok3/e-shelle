from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _



# =====================================================
# 📘 CATALOGUE D’EXAMENS
# =====================================================

class Exam(models.Model):
    code = models.SlugField(
        unique=True,
        help_text=_("Code court: tcf, tef, ielts, celpip, goethe, testdaf")
    )
    name = models.CharField(max_length=100)
    language = models.CharField(
        max_length=2,
        choices=[("fr", "Français"), ("en", "Anglais"), ("de", "Allemand")],
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("Examen")
        verbose_name_plural = _("Examens")

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

    class Meta:
        ordering = ["exam", "order"]

    def __str__(self):
        return f"{self.exam.code.upper()} — {self.code.upper()}"


# =====================================================
# 📚 CONTENUS
# =====================================================

class Passage(models.Model):
    title = models.CharField(max_length=200, blank=True)
    text = models.TextField()

    def __str__(self):
        return self.title or f"Passage #{self.pk}"

class Asset(models.Model):
    KIND_CHOICES = (
        ("audio", "Audio"),
        ("image", "Image"),
        ("video", "Video"),
    )

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    file = models.FileField(upload_to="audio/", blank=True, null=True)
    lang = models.CharField(max_length=10, default="fr")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} - {self.lang}"


# =====================================================
# 📝 QUESTIONS D’EXAMEN (BANQUE)
# =====================================================

class Question(models.Model):
    SUBTYPE_CHOICES = [
        ("mcq", "QCM"),
        ("short", "Texte court"),
    ]

    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name="questions")
    subtype = models.CharField(max_length=10, choices=SUBTYPE_CHOICES, default="mcq")
    stem = models.TextField()
    passage = models.ForeignKey(Passage, on_delete=models.SET_NULL, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
    difficulty = models.FloatField(default=0.5)

    def __str__(self):
        return f"Q{self.pk}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:40]


class Explanation(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name="explanation")
    text_md = models.TextField()


# =====================================================
# ⏱️ SESSIONS
# =====================================================

class Session(models.Model):
    MODE_CHOICES = [
        ("practice", "Entraînement"),
        ("mock", "Examen blanc"),
    ]

    user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="prep_sessions"
)

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="practice")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class Attempt(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE)
    raw_score = models.FloatField(default=0)
    total_items = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("session", "section")


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    payload = models.JSONField(default=dict)
    is_correct = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("attempt", "question")


# =====================================================
# 📖 COURS & EXERCICES (TEF / TCF)
# =====================================================

class CourseLesson(models.Model):
    SECTION_CHOICES = [
        ("co", "Compréhension orale"),
        ("ce", "Compréhension écrite"),
        ("ee", "Expression écrite"),
        ("eo", "Expression orale"),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="course_lessons")
    section = models.CharField(max_length=2, choices=SECTION_CHOICES)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    locale = models.CharField(
        max_length=2,
        choices=[("fr", "Français"), ("en", "English"), ("de", "Deutsch")],
        default="fr",
    )
    content_html = models.TextField()
    order = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["exam", "section", "order", "id"]

    def __str__(self):
        return self.title


class CourseExercise(models.Model):
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name="exercises")
    title = models.CharField(max_length=200)
    instruction = models.TextField(blank=True)
    question_text = models.TextField()

    option_a = models.CharField(max_length=255, blank=True)
    option_b = models.CharField(max_length=255, blank=True)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)

    correct_option = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        blank=True,
    )

    audio = models.FileField(upload_to="course_exercises/audio/", blank=True, null=True)
    image = models.ImageField(upload_to="course_exercises/images/", blank=True, null=True)

    summary = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["lesson", "order", "id"]

    def __str__(self):
        return self.title

    @property
    def is_mcq(self):
        """
        🔒 FORÇAGE QCM :
        Dès qu'il existe au moins A et B,
        l'exercice est considéré comme répondable.
        """
        return bool(self.option_a and self.option_b)




class UserSkillProgress(models.Model):
    SKILL_CHOICES = [
        ("co", "Compréhension orale"),
        ("ce", "Compréhension écrite"),
        ("ee", "Expression écrite"),
        ("eo", "Expression orale"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skill_progress",
    )
    exam_code = models.CharField(max_length=20)  # tef, tcf, delf…
    skill = models.CharField(max_length=2, choices=SKILL_CHOICES)

    score_percent = models.PositiveIntegerField(default=0)
    total_attempts = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "exam_code", "skill")

    def __str__(self):
        return f"{self.user} – {self.exam_code.upper()} {self.skill} ({self.score_percent}%)"





class UserSkillResult(models.Model):
    SKILL_CHOICES = [
        ("co", "Compréhension orale"),
        ("ce", "Compréhension écrite"),
        ("ee", "Expression écrite"),
        ("eo", "Expression orale"),
    ]

    EXAM_CHOICES = [
        ("tef", "TEF"),
        ("tcf", "TCF"),
    ]

    SESSION_TYPE_CHOICES = [
        ("training", "Entraînement"),
        ("mock", "Examen blanc"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skill_results"
    )

    exam_code = models.CharField(max_length=10, choices=EXAM_CHOICES)
    skill = models.CharField(max_length=2, choices=SKILL_CHOICES)
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE_CHOICES)

    score_percent = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} – {self.exam_code.upper()} {self.skill.upper()} – {self.score_percent}%"


