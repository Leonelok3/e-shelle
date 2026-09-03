from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("adgen", "0006_adcampaign_photo_produit_2_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SoraCreditWallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credits_4s", models.PositiveIntegerField(default=0, verbose_name="Credits Sora 4s")),
                ("credits_8s", models.PositiveIntegerField(default=0, verbose_name="Credits Sora 8s")),
                ("credits_12s", models.PositiveIntegerField(default=0, verbose_name="Credits Sora 12s")),
                ("used_4s", models.PositiveIntegerField(default=0, verbose_name="Sora 4s utilises")),
                ("used_8s", models.PositiveIntegerField(default=0, verbose_name="Sora 8s utilises")),
                ("used_12s", models.PositiveIntegerField(default=0, verbose_name="Sora 12s utilises")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adgen_sora_wallet",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Utilisateur",
                    ),
                ),
            ],
            options={
                "verbose_name": "Portefeuille Sora",
                "verbose_name_plural": "Portefeuilles Sora",
            },
        ),
    ]
