from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resto", "0003_notification_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="restaurant",
            name="description_en",
            field=models.TextField(blank=True, verbose_name="Description (English)"),
        ),
    ]
