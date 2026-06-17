from django.db import migrations, models


class Migration(migrations.Migration):
    """Creation de la table des prestataires Shelle Premium."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Prestataire",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom_complet", models.CharField(max_length=200)),
                ("code_premium", models.CharField(max_length=50, unique=True)),
                ("date_expiration", models.CharField(max_length=5)),
                ("adresse", models.TextField()),
                ("date_inscription", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Prestataire Shelle Premium",
                "verbose_name_plural": "Prestataires Shelle Premium",
                "ordering": ["-date_inscription"],
            },
        ),
    ]

