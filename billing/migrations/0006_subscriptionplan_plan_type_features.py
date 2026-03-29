from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0005_receipt"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="plan_type",
            field=models.CharField(
                choices=[("candidate", "Candidat"), ("recruiter", "Recruteur")],
                default="candidate",
                max_length=20,
                verbose_name="Type de plan",
            ),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="features",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
