import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp_agent", "0017_whatsapp_webhook_health"),
        ("whatsapp_commerce", "0006_businesswhatsappcontact_consent_marketing_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="messageenvoi",
            name="business_contact",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="campaign_messages",
                to="whatsapp_commerce.businesswhatsappcontact",
            ),
        ),
    ]
