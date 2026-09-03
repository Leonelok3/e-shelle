from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0029_businessprofile_country"),
    ]

    operations = [
        migrations.AlterField(
            model_name="businesscatalogitem",
            name="video_url",
            field=models.URLField(
                blank=True,
                help_text="Lien de la vidéo (Cloudinary, YouTube, TikTok...)",
                max_length=2048,
                null=True,
            ),
        ),
    ]
