from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_adgen_studio_plans"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="whatsapp_marketing_opt_in",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customuser",
            name="whatsapp_marketing_opted_out",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customuser",
            name="whatsapp_marketing_opt_in_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]