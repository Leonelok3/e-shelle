import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("whatsapp_agent", "0011_campaign_meta_template"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="contactwhatsapp",
            name="call_permission_status",
            field=models.CharField(default="no_permission", max_length=20),
        ),
        migrations.AddField(
            model_name="contactwhatsapp",
            name="call_permission_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="WhatsAppCall",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("meta_call_id", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("direction", models.CharField(choices=[("inbound", "Entrant"), ("outbound", "Sortant")], max_length=10)),
                ("status", models.CharField(choices=[("pending", "En attente"), ("ringing", "Sonnerie"), ("connecting", "Connexion"), ("active", "En cours"), ("rejected", "Refuse"), ("ended", "Termine"), ("failed", "Echec")], db_index=True, default="pending", max_length=20)),
                ("sdp_offer", models.TextField(blank=True)),
                ("sdp_answer", models.TextField(blank=True)),
                ("error", models.TextField(blank=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("contact", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calls", to="whatsapp_agent.contactwhatsapp")),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calls", to="whatsapp_agent.conversationwhatsapp")),
                ("initiated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="whatsapp_calls", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="whatsappcall",
            index=models.Index(fields=["status", "created_at"], name="whatsapp_ag_status_5836b2_idx"),
        ),
    ]