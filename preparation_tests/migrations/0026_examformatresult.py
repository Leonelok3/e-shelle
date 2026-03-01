from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("preparation_tests", "0025_studyplanprogress_is_completed_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExamFormatResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("exam_code", models.CharField(
                    choices=[("tef","TEF Canada"),("tcf","TCF Canada"),("delf","DELF"),("dalf","DALF")],
                    db_index=True, max_length=6,
                )),
                ("level", models.CharField(
                    choices=[("A1","A1"),("A2","A2"),("B1","B1"),("B2","B2"),("C1","C1"),("C2","C2")],
                    db_index=True, max_length=2,
                )),
                ("co_correct",   models.PositiveIntegerField(default=0)),
                ("co_total",     models.PositiveIntegerField(default=0)),
                ("ce_correct",   models.PositiveIntegerField(default=0)),
                ("ce_total",     models.PositiveIntegerField(default=0)),
                ("co_pct",       models.PositiveIntegerField(default=0)),
                ("ce_pct",       models.PositiveIntegerField(default=0)),
                ("global_pct",   models.PositiveIntegerField(default=0)),
                ("co_score",     models.PositiveIntegerField(default=0)),
                ("ce_score",     models.PositiveIntegerField(default=0)),
                ("global_score", models.PositiveIntegerField(default=0)),
                ("score_max",    models.PositiveIntegerField(default=50)),
                ("cefr_co",      models.CharField(blank=True, max_length=10)),
                ("cefr_ce",      models.CharField(blank=True, max_length=10)),
                ("cefr_global",  models.CharField(blank=True, max_length=10)),
                ("passed",       models.BooleanField(blank=True, null=True)),
                ("taken_at",     models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="exam_format_results",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Résultat examen officiel",
                "verbose_name_plural": "Résultats examens officiels",
                "ordering": ["-taken_at"],
            },
        ),
    ]
