# Generated for bilingual AI delivery kit content.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("business", "0032_bilingual_app_promo_slides")]

    operations = [
        migrations.AddField(
            model_name="clientaikit",
            name="content_en",
            field=models.JSONField(blank=True, default=dict, verbose_name="English content"),
        ),
    ]
