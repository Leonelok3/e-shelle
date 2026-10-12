# Add optional English fields for service offers and portfolio content.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0001_initial")]

    operations = [
        migrations.AddField("offreservice", "titre_en", models.CharField(blank=True, max_length=200)),
        migrations.AddField("offreservice", "description_en", models.TextField(blank=True)),
        migrations.AddField("offreservice", "features_en", models.JSONField(blank=True, default=list)),
        migrations.AddField("categoriaportfolio", "nom_en", models.CharField(blank=True, max_length=100)),
        migrations.AddField("projetportfolio", "titre_en", models.CharField(blank=True, max_length=200)),
        migrations.AddField("projetportfolio", "description_en", models.TextField(blank=True)),
    ]
