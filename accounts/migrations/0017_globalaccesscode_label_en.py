from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0016_appplan_english_content")]

    operations = [
        migrations.AddField("globalaccesscode", "label_en", models.CharField(blank=True, max_length=150)),
    ]
