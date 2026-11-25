import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ocd_live", "0003_livebooking_boutique_active_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="livebooking",
            name="management_token",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="Jeton privé de gestion",
            ),
        ),
        migrations.AddField(
            model_name="livebooking",
            name="payment_validated_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Date de validation du paiement",
            ),
        ),
        migrations.AlterField(
            model_name="livebooking",
            name="boutique_active",
            field=models.BooleanField(
                default=False,
                verbose_name="Boutique Live Publique Active",
            ),
        ),
    ]
