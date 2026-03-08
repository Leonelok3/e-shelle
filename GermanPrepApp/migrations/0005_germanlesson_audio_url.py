from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GermanPrepApp", "0004_germanexam_integration_choice"),
    ]

    operations = [
        migrations.AddField(
            model_name="germanlesson",
            name="audio_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Chemin relatif MEDIA vers le fichier audio (généré par TTS pour HÖREN).",
                max_length=500,
            ),
        ),
    ]
