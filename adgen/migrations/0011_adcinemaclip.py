from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("adgen", "0010_adcampaign_offer")]
    operations = [
        migrations.CreateModel(
            name="AdCinemaClip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_id", models.UUIDField(blank=True, null=True)),
                ("state", models.CharField(default="submitted", max_length=16)),
                ("video", models.FileField(blank=True, upload_to="adgen/cinema/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("campaign", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="cinema_clip", to="adgen.adcampaign")),
            ],
        ),
    ]
