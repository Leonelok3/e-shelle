from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0002_alter_parametreplateforme_telephone_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="parametreplateforme",
            name="produits_services_hero_image",
            field=models.ImageField(
                blank=True,
                help_text="Visuel affiche dans le hero de la page Produits & Services.",
                null=True,
                upload_to="config/heros/",
            ),
        ),
    ]
