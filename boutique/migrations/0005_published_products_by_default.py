from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("boutique", "0004_commande_whatsapp_draft_order_and_more")]

    operations = [
        migrations.AlterField(
            model_name="produit",
            name="is_published",
            field=models.BooleanField(default=True),
        ),
    ]
