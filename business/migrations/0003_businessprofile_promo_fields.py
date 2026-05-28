from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0002_businessprofile_description_paymentrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessprofile",
            name="promo_headline",
            field=models.CharField(
                blank=True,
                help_text="Titre court affiche sur la page d'accueil.",
                max_length=140,
            ),
        ),
        migrations.AddField(
            model_name="businessprofile",
            name="promo_offer",
            field=models.CharField(
                blank=True,
                help_text="Offre, phrase d'accroche ou avantage commercial.",
                max_length=160,
            ),
        ),
        migrations.AddField(
            model_name="businessprofile",
            name="promo_image",
            field=models.ImageField(
                blank=True,
                help_text="Visuel publicitaire affiche dans le hero et les sections premium.",
                null=True,
                upload_to="business/promos/",
            ),
        ),
        migrations.AddField(
            model_name="businessprofile",
            name="promo_url",
            field=models.URLField(
                blank=True,
                help_text="Lien de destination de la publicite. Laisser vide pour utiliser WhatsApp ou le module.",
            ),
        ),
    ]
