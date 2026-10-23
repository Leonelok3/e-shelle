import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def challenge_upload_path(instance, filename):
    token = getattr(instance, "public_token", None) or getattr(instance, "access_token", None)
    if token is None:
        token = instance.submission.access_token
    return f"edu_platform/challenges/{token}/{uuid.uuid4().hex}_{filename[:80]}"


class DailyChallenge(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publié"
        CLOSED = "closed", "Clôturé"

    title = models.CharField(max_length=180)
    instructions = models.TextField(blank=True)
    subject = models.ForeignKey("edu_platform.Subject", on_delete=models.SET_NULL, null=True, blank=True, related_name="challenges")
    level = models.CharField(max_length=40, blank=True)
    exercise_file = models.FileField(upload_to=challenge_upload_path, blank=True)
    answer_key = models.TextField(help_text="Corrigé attendu : l’IA s’appuie dessus pour noter.")
    rubric = models.TextField(blank=True, help_text="Critères et répartition des points. Indiquez le total.")
    total_points = models.PositiveSmallIntegerField(default=20, validators=[MinValueValidator(1)])
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    leaderboard_enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_edu_challenges")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-starts_at", "-id"]

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        now = timezone.now()
        return self.status == self.Status.PUBLISHED and self.starts_at <= now and (not self.ends_at or now <= self.ends_at)


class ChallengeSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "À corriger"
        PROCESSING = "processing", "Correction en cours"
        GRADED = "graded", "Corrigé par IA (provisoire)"
        REVIEWED = "reviewed", "Vérifié par un enseignant"
        FAILED = "failed", "Correction à reprendre"

    challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE, related_name="submissions")
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="edu_challenge_submissions")
    student_name = models.CharField(max_length=120)
    student_class = models.CharField(max_length=80, blank=True)
    show_name_on_leaderboard = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=240, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_edu_challenge_submissions")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-score", "submitted_at"]

    def __str__(self):
        return f"{self.student_name} — {self.challenge}"


class SubmissionFile(models.Model):
    submission = models.ForeignKey(ChallengeSubmission, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=challenge_upload_path)
    original_name = models.CharField(max_length=180, blank=True)
    mime_type = models.CharField(max_length=80)
    size_bytes = models.PositiveIntegerField()

    def __str__(self):
        return self.original_name or self.file.name
