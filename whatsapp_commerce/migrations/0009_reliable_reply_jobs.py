import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("whatsapp_commerce", "0008_businesswhatsappconnection_last_meta_sync_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="businesswhatsappcontact",
            name="agent_paused",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="BusinessWhatsAppReplyJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number_id", models.CharField(max_length=64)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Réponse en attente"),
                        ("processing", "Réponse en cours"),
                        ("sent", "Réponse envoyée"),
                        ("skipped", "Réponse automatique ignorée"),
                        ("review", "Intervention de l’équipe"),
                    ],
                    default="pending",
                    max_length=12,
                )),
                ("dispatch_after", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("connection", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="whatsapp_commerce.businesswhatsappconnection",
                )),
                ("message", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="reply_job",
                    to="whatsapp_commerce.businesswhatsappmessage",
                )),
            ],
            options={"indexes": [
                models.Index(fields=["status", "dispatch_after"], name="wa_reply_due_idx"),
                models.Index(fields=["status", "updated_at"], name="wa_reply_state_idx"),
            ]},
        ),
    ]
