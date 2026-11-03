import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("preparation_tests", "0031_courseexercise_document_text_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TCFDailyProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day", models.DateField()),
                ("skill", models.CharField(max_length=2)),
                ("topic", models.CharField(blank=True, max_length=160)),
                ("task_number", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("objective_correct", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("objective_total", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("ai_score", models.FloatField(blank=True, null=True)),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("elapsed_seconds", models.PositiveIntegerField(default=0)),
                ("overtime", models.BooleanField(default=False)),
                ("production", models.TextField(blank=True)),
                ("answers", models.JSONField(blank=True, default=dict)),
                ("coaching", models.JSONField(blank=True, default=dict)),
                ("completed_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tcf_daily_progress", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-day"]},
        ),
        migrations.AddConstraint(
            model_name="tcfdailyprogress",
            constraint=models.UniqueConstraint(fields=("user", "day"), name="uniq_tcf_daily_progress_user_day"),
        ),
        migrations.AddIndex(
            model_name="tcfdailyprogress",
            index=models.Index(fields=["user", "day"], name="tcf_daily_user_day_idx"),
        ),
    ]
