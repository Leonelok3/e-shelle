from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('germany_opportunities', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GermanCVProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=30)),
                ('address', models.CharField(blank=True, max_length=300, help_text='Adresse actuelle (pays + ville)')),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('nationality', models.CharField(default='Camerounaise', max_length=100)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='lebenslauf/photos/')),
                ('linkedin', models.URLField(blank=True)),
                ('german_level', models.CharField(choices=[('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'), ('B2', 'B2'), ('C1', 'C1'), ('C2', 'C2')], default='B1', max_length=5)),
                ('goethe_certified', models.BooleanField(default=False)),
                ('goethe_cert_date', models.DateField(blank=True, null=True)),
                ('target_sector', models.CharField(blank=True, max_length=100)),
                ('target_cities', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Profil CV'},
        ),
        migrations.CreateModel(
            name='CVExperience',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('company', models.CharField(max_length=200)),
                ('city', models.CharField(max_length=100)),
                ('country', models.CharField(default='Cameroun', max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_current', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=1)),
            ],
            options={'verbose_name': 'Experience', 'ordering': ['-start_date']},
        ),
        migrations.CreateModel(
            name='CVEducation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('degree', models.CharField(max_length=200)),
                ('school', models.CharField(max_length=200)),
                ('city', models.CharField(max_length=100)),
                ('country', models.CharField(default='Cameroun', max_length=100)),
                ('start_year', models.IntegerField()),
                ('end_year', models.IntegerField(blank=True, null=True)),
                ('description', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=1)),
            ],
            options={'verbose_name': 'Formation', 'ordering': ['-start_year']},
        ),
        migrations.CreateModel(
            name='CVLanguage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(max_length=50)),
                ('proficiency', models.CharField(choices=[('Muttersprache', 'Langue maternelle'), ('verhandlungssicher', 'Courant (C1/C2)'), ('fliessend', 'Courant (B2)'), ('gute Kenntnisse', 'Bon niveau (B1)'), ('Grundkenntnisse', 'Notions (A1/A2)')], max_length=30)),
                ('certificate', models.CharField(blank=True, max_length=100)),
            ],
            options={'verbose_name': 'Langue', 'ordering': ['language']},
        ),
        migrations.CreateModel(
            name='GeneratedLebenslauf',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('custom_offer_title', models.CharField(blank=True, max_length=300)),
                ('custom_offer_company', models.CharField(blank=True, max_length=200)),
                ('content_html', models.TextField()),
                ('content_pdf', models.FileField(blank=True, null=True, upload_to='lebenslauf/pdfs/')),
                ('ai_cover_letter', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('offer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lebenslauf_set', to='germany_opportunities.ausbildungoffer')),
            ],
            options={'verbose_name': 'Lebenslauf genere', 'ordering': ['-created_at']},
        ),
    ]
