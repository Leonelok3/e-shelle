from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GermanPrepApp', '0003_germantestsession_duration_seconds'),
    ]

    operations = [
        migrations.AlterField(
            model_name='germanexam',
            name='exam_type',
            field=models.CharField(
                choices=[
                    ('GOETHE', 'Goethe-Zertifikat'),
                    ('TELC', 'telc Deutsch'),
                    ('TESTDAF', 'TestDaF'),
                    ('DSH', 'DSH'),
                    ('GENERAL', 'Général / Visa'),
                    ('INTEGRATION', "Test d'intégration"),
                ],
                default='GENERAL',
                max_length=20,
            ),
        ),
    ]
