from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("preparation_tests", "0028_merge_0026_examformatresult_0027_mockexamresult"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeaturedContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(
                    choices=[("fr", "Français"), ("de", "Allemand"), ("en", "Anglais")],
                    db_index=True, default="fr", max_length=5,
                )),
                ("section", models.CharField(
                    choices=[
                        ("co", "Compréhension Orale"),
                        ("ce", "Compréhension Écrite"),
                        ("eo", "Expression Orale"),
                        ("ee", "Expression Écrite"),
                        ("general", "Général"),
                    ],
                    db_index=True, default="general", max_length=10,
                )),
                ("content_type", models.CharField(
                    choices=[
                        ("monthly", "Sujet du mois"),
                        ("subject", "Sujet officiel"),
                        ("correction", "Correction officielle"),
                        ("tip", "Conseil / Astuce"),
                    ],
                    default="subject", max_length=15, verbose_name="Type",
                )),
                ("title", models.CharField(max_length=200, verbose_name="Titre")),
                ("subtitle", models.CharField(blank=True, max_length=300, verbose_name="Sous-titre")),
                ("description", models.TextField(blank=True, verbose_name="Description courte")),
                ("content_html", models.TextField(blank=True, verbose_name="Contenu HTML (correction, conseils…)")),
                ("pdf_file", models.FileField(
                    blank=True, null=True,
                    upload_to="featured_content/",
                    verbose_name="Fichier PDF (sujet / correction)",
                )),
                ("is_premium", models.BooleanField(
                    default=False,
                    help_text="Cocher = visible seulement pour les abonnés",
                    verbose_name="Réservé Premium",
                )),
                ("is_published", models.BooleanField(default=True, verbose_name="Publié")),
                ("month", models.DateField(
                    blank=True, null=True,
                    help_text="Mettre le 1er du mois concerné, ex: 2026-04-01",
                    verbose_name="Mois (pour 'Sujet du mois')",
                )),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Contenu mis en avant",
                "verbose_name_plural": "Contenus mis en avant",
                "ordering": ["-month", "order", "-created_at"],
            },
        ),
    ]
