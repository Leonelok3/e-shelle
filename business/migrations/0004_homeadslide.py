from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0003_businessprofile_promo_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeAdSlide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("subtitle", models.CharField(blank=True, max_length=190)),
                ("image", models.ImageField(upload_to="business/home-slides/")),
                ("badge", models.CharField(blank=True, default="Premium", max_length=60)),
                ("cta_label", models.CharField(blank=True, default="Commander", max_length=40)),
                (
                    "cta_url",
                    models.URLField(
                        blank=True,
                        help_text="Lien de commande. Si vide, E-Shelle utilise WhatsApp ou la recherche IA du business.",
                    ),
                ),
                ("city", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "business",
                    models.ForeignKey(
                        blank=True,
                        help_text="Business premium/business associe au slide.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="home_ad_slides",
                        to="business.businessprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Slide publicitaire accueil",
                "verbose_name_plural": "Slides publicitaires accueil",
                "ordering": ["order", "-created_at"],
            },
        ),
    ]
