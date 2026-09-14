from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp_agent", "0006_contact_consentement_and_optout"),
    ]

    operations = [
        migrations.CreateModel(
            name="OutreachLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("canal", models.CharField(choices=[("whatsapp", "WhatsApp"), ("email", "Email")], max_length=20)),
                ("identifiant", models.CharField(db_index=True, max_length=320)),
                ("statut", models.CharField(default="envoye", max_length=30)),
                ("sujet", models.CharField(blank=True, max_length=255)),
                ("envoye_le", models.DateTimeField(auto_now_add=True)),
                ("campagne", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="outreach_logs", to="whatsapp_agent.campagne")),
                ("message_envoi", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="outreach_log", to="whatsapp_agent.messageenvoi")),
            ],
            options={"ordering": ["-envoye_le"]},
        ),
        migrations.AddIndex(
            model_name="outreachlog",
            index=models.Index(fields=["canal", "identifiant", "envoye_le"], name="whatsapp_ag_canal_6f0e33_idx"),
        ),
    ]