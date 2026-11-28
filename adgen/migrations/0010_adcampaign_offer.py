from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("adgen", "0009_studiousage_is_trial")]
    operations = [
        migrations.AddField(model_name="adcampaign", name="offer_kind", field=models.CharField(blank=True, max_length=10)),
        migrations.AddField(model_name="adcampaign", name="offer_id", field=models.PositiveBigIntegerField(blank=True, null=True)),
    ]
