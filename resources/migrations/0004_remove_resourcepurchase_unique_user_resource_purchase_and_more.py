from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0003_resource_store_fields_resourcepurchase"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="resourcepurchase",
            unique_together=set(),
        ),
        migrations.RemoveConstraint(
            model_name="resourcepurchase",
            name="unique_user_resource_purchase",
        ),
        migrations.AlterField(
            model_name="resource",
            name="file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="resources/",
                verbose_name="Fichier à télécharger",
            ),
        ),
        migrations.AlterField(
            model_name="resource",
            name="file_size",
            field=models.CharField(
                blank=True,
                help_text="Ex : 2.4 Mo — calculé automatiquement si vide",
                max_length=20,
                verbose_name="Taille affichée",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="resourcepurchase",
            unique_together={("user", "resource")},
        ),
    ]
