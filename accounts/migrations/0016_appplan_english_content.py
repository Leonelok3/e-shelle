from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0015_customuser_whatsapp_marketing_consent")]

    operations = [
        migrations.AddField("appplan", "name_en", models.CharField(blank=True, max_length=100)),
        migrations.AddField("appplan", "description_en", models.TextField(blank=True)),
        migrations.AddField("appplan", "features_en", models.JSONField(blank=True, default=list)),
    ]
