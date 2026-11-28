from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("adgen", "0010_adcampaign_offer"), ("whatsapp_commerce", "0020_catalog_and_campaign_history")]
    operations = [
        migrations.AddField(
            model_name="whatsappofferclick", name="adgen_render",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="adgen.studiousage"),
        ),
    ]
