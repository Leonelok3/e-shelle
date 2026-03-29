from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cv_generator', '0004_alter_certification_options_alter_competence_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cv',
            name='photo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='cv/photos/',
                verbose_name='Photo de profil',
                help_text='Photo optionnelle pour le CV Europe/Modern',
            ),
        ),
    ]
