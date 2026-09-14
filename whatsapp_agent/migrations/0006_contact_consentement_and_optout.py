from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp_agent", "0005_campagne_destinataires_contacts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contactwhatsapp",
            name="consentement_confirme",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="contactwhatsapp",
            name="consentement_source",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="contactwhatsapp",
            name="consentement_le",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contactwhatsapp",
            name="desinscrit",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="contactwhatsapp",
            name="desinscrit_le",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]