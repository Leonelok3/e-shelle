from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0036_businessprofile_facebook_shared_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessactivationcode",
            name="unlocks_whatsapp_onboarding",
            field=models.BooleanField(
                default=False,
                help_text="À cocher uniquement après vérification manuelle du paiement de l'offre WhatsApp officiel.",
                verbose_name="Débloquer aussi WhatsApp officiel",
            ),
        ),
    ]
