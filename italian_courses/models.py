# italian_courses/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class CourseCategory(models.Model):
    """
    Regroupe des leçons par thème/niveau (ex: Débutant, Voyage, Grammaire…).
    """
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Course category"
        verbose_name_plural = "Course categories"

    def __str__(self) -> str:
        return self.name


class Lesson(models.Model):
    """
    Une seule classe Lesson (non abstract).
    Supporte contenu HTML + audio + transcript.
    """
    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.PROTECT,
        related_name="lessons",
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)

    # Contenu HTML (tu peux stocker du HTML complet)
    content_html = models.TextField(blank=True)

    # Audio (mp3/wav/etc.) - nécessite MEDIA_ROOT/MEDIA_URL configurés
    audio_file = models.FileField(
        upload_to="italian_courses/audio/",
        blank=True,
        null=True,
    )

    # Transcript (texte brut)
    transcript = models.TextField(blank=True)

    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    # Optionnel mais utile
    estimated_minutes = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category__order", "category__name", "order", "title")
        constraints = [
            models.UniqueConstraint(
                fields=["category", "slug"],
                name="uniq_lesson_slug_per_category",
            )
        ]
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"

    def __str__(self) -> str:
        return self.title


class Quiz(models.Model):
    """
    Un quiz attaché à une Lesson (ForeignKey clair vers Lesson).
    """
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("lesson__order", "order", "title")
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"

    def __str__(self) -> str:
        return f"{self.lesson.title} — {self.title}"


class Question(models.Model):
    """
    Questions d'un Quiz.
    """
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    prompt = models.TextField()
    explanation = models.TextField(blank=True)

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("quiz__order", "order", "id")
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self) -> str:
        return f"Q{self.order + 1} — {self.quiz.title}"


class Choice(models.Model):
    """
    Choix possibles d'une Question.
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
    )

    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("question__order", "order", "id")
        verbose_name = "Choice"
        verbose_name_plural = "Choices"

    def __str__(self) -> str:
        return f"{self.text[:60]}"


class LessonProgress(models.Model):
    """
    Suivi de progression d’un utilisateur sur une leçon.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="italian_lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_records",
    )

    # Progression simple
    progress_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Pourcentage entre 0.00 et 100.00",
    )
    completed = models.BooleanField(default=False)

    # Optionnel : position audio, utile pour reprise
    last_position_seconds = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(default=timezone.now)
    last_accessed_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-last_accessed_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"],
                name="uniq_progress_per_user_lesson",
            )
        ]
        indexes = [
            models.Index(fields=["user", "lesson"]),
            models.Index(fields=["lesson", "completed"]),
        ]
        verbose_name = "Lesson progress"
        verbose_name_plural = "Lesson progress"

    def __str__(self) -> str:
        return f"{self.user} — {self.lesson} ({self.progress_percent}%)"

    def mark_completed(self) -> None:
        self.completed = True
        self.progress_percent = 100.00
        if self.completed_at is None:
            self.completed_at = timezone.now()
