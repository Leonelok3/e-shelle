from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("njangi", "0016_alter_group_frequency")]
    operations = [
        migrations.AddField(
            model_name="session", name="proposals",
            field=models.TextField(blank=True, verbose_name="Propositions et divers"),
        ),
    ]
