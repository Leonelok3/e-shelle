from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        (
            "preparation_tests",
            "0006_delete_coexercise_delete_listeningexercise_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="section",
            field=models.ForeignKey(
                to="preparation_tests.examsection",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sessions",
            ),
        ),
        migrations.AddField(
            model_name="session",
            name="total_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="session",
            name="duration_sec",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attempt",
            name="score_percent",
            field=models.FloatField(default=0),
        ),
    ]
