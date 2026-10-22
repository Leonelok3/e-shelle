from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0033_client_ai_kit_english_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="businesscatalogitem",
            name="category",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="businesscatalogitem",
            name="prix_gros_xaf",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="businesscatalogitem",
            name="sku",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="businesscatalogitem",
            name="stock_quantity",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Quantite en stock (laisser vide si non suivi).",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="businesscatalogitem",
            constraint=models.UniqueConstraint(
                condition=~models.Q(sku=""),
                fields=("business", "sku"),
                name="business_catalog_sku_uniq",
            ),
        ),
    ]
