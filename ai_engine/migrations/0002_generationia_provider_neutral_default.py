from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai_engine', '0001_initial')]

    operations = [
        migrations.AlterField(
            model_name='generationia',
            name='modele',
            field=models.CharField(default='', help_text='Modèle IA utilisé', max_length=100),
        ),
    ]
