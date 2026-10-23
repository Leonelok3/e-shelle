import django.db.models.deletion
import django.core.validators
import django.utils.timezone
import edu_platform.models.challenge
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("edu_platform", "0003_alter_examdocument_options_alter_subject_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyChallenge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("instructions", models.TextField(blank=True)),
                ("level", models.CharField(blank=True, max_length=40)),
                ("exercise_file", models.FileField(blank=True, upload_to=edu_platform.models.challenge.challenge_upload_path)),
                ("answer_key", models.TextField(help_text="Corrigé attendu : l’IA s’appuie dessus pour noter.")),
                ("rubric", models.TextField(blank=True, help_text="Critères et répartition des points. Indiquez le total.")),
                ("total_points", models.PositiveSmallIntegerField(default=20, validators=[django.core.validators.MinValueValidator(1)])),
                ("public_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("draft", "Brouillon"), ("published", "Publié"), ("closed", "Clôturé")], db_index=True, default="draft", max_length=12)),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("leaderboard_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_edu_challenges", to=settings.AUTH_USER_MODEL)),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="challenges", to="edu_platform.subject")),
            ],
            options={"ordering": ["-starts_at", "-id"]},
        ),
        migrations.CreateModel(
            name="ChallengeSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("access_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("student_name", models.CharField(max_length=120)),
                ("student_class", models.CharField(blank=True, max_length=80)),
                ("show_name_on_leaderboard", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("pending", "À corriger"), ("processing", "Correction en cours"), ("graded", "Corrigé par IA (provisoire)"), ("reviewed", "Vérifié par un enseignant"), ("failed", "Correction à reprendre")], db_index=True, default="pending", max_length=12)),
                ("score", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("feedback", models.JSONField(blank=True, default=dict)),
                ("error_message", models.CharField(blank=True, max_length=240)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("graded_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("challenge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submissions", to="edu_platform.dailychallenge")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_edu_challenge_submissions", to=settings.AUTH_USER_MODEL)),
                ("student", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="edu_challenge_submissions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-score", "submitted_at"]},
        ),
        migrations.CreateModel(
            name="SubmissionFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=edu_platform.models.challenge.challenge_upload_path)),
                ("original_name", models.CharField(blank=True, max_length=180)),
                ("mime_type", models.CharField(max_length=80)),
                ("size_bytes", models.PositiveIntegerField()),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="files", to="edu_platform.challengesubmission")),
            ],
        ),
    ]
