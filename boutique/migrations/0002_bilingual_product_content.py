from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("boutique", "0001_initial")]

    operations = [
        migrations.AddField("categorieproduit", "nom_en", models.CharField(blank=True, max_length=100)),
        migrations.AddField("produit", "titre_en", models.CharField(blank=True, max_length=200)),
        migrations.AddField("produit", "description_en", models.TextField(blank=True)),
        migrations.AddField("produit", "description_courte_en", models.CharField(blank=True, max_length=300)),
    ]
