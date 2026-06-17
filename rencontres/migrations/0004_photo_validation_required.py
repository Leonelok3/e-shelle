from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rencontres", "0003_love_manual_subscription_plans"),
    ]

    operations = [
        migrations.AlterField(
            model_name="photoprofil",
            name="est_approuvee",
            field=models.BooleanField(default=False),
        ),
    ]
