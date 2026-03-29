from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="resource",
            name="cover_image",
            field=models.ImageField(blank=True, null=True, upload_to="resources/covers/", verbose_name="Image de couverture"),
        ),
        migrations.AddField(
            model_name="resource",
            name="price_xaf",
            field=models.PositiveIntegerField(default=0, help_text="0 = gratuit", verbose_name="Prix (XAF)"),
        ),
        migrations.AddField(
            model_name="resource",
            name="price_eur",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=6, verbose_name="Prix (EUR)"),
        ),
        migrations.AddField(
            model_name="resource",
            name="is_free",
            field=models.BooleanField(default=False, verbose_name="Gratuit"),
        ),
        migrations.AddField(
            model_name="resource",
            name="preview_url",
            field=models.URLField(blank=True, default="", verbose_name="Aperçu (lien externe)"),
        ),
    ]
