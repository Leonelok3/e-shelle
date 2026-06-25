from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AusbildungOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ref_nr', models.CharField(db_index=True, max_length=100, unique=True)),
                ('title', models.CharField(max_length=300)),
                ('company', models.CharField(max_length=200)),
                ('city', models.CharField(max_length=100)),
                ('postal_code', models.CharField(blank=True, max_length=10)),
                ('region', models.CharField(blank=True, max_length=100)),
                ('sector', models.CharField(choices=[('gesundheit', 'Gesundheit & Pflege (Sante)'), ('it', 'IT & Informatik'), ('elektro', 'Elektrotechnik & Mechatronik'), ('bau', 'Bau & Handwerk'), ('hotellerie', 'Hotellerie & Gastronomie'), ('logistik', 'Logistik & Transport'), ('kaufmann', 'Kaufmann / Buero'), ('soziales', 'Soziales & Erziehung'), ('andere', 'Autre')], default='andere', max_length=20)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('salary_month', models.CharField(blank=True, max_length=50)),
                ('language_req', models.CharField(choices=[('B1', 'B1 (intermediaire)'), ('B2', 'B2 (intermediaire superieur)'), ('C1', 'C1 (avance)'), ('A2', 'A2 (elementaire)')], default='B1', max_length=5)),
                ('duration_months', models.IntegerField(default=36)),
                ('description', models.TextField(blank=True)),
                ('url_apply', models.URLField(max_length=500)),
                ('ai_summary_fr', models.TextField(blank=True, help_text='Resume en francais genere par GPT pour les candidats africains')),
                ('ai_tips_fr', models.TextField(blank=True, help_text='Conseils de candidature specifiques generes par IA')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('fetched_at', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Offre Ausbildung',
                'verbose_name_plural': 'Offres Ausbildung',
                'ordering': ['-fetched_at'],
            },
        ),
        migrations.CreateModel(
            name='ScholarshipOpportunity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('provider', models.CharField(max_length=200)),
                ('level', models.CharField(choices=[('ausbildung', 'Ausbildung (Formation pro)'), ('bachelor', 'Licence'), ('master', 'Master'), ('phd', 'Doctorat'), ('research', 'Recherche'), ('language', 'Cours de langue')], max_length=20)),
                ('deadline', models.DateField(blank=True, null=True)),
                ('amount', models.CharField(blank=True, max_length=200)),
                ('description', models.TextField()),
                ('url', models.URLField(max_length=500)),
                ('countries', models.CharField(blank=True, max_length=500)),
                ('ai_summary_fr', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('fetched_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Bourse / Opportunite',
                'verbose_name_plural': 'Bourses / Opportunites',
                'ordering': ['deadline', '-fetched_at'],
            },
        ),
        migrations.CreateModel(
            name='UserOpportunityBookmark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('saved_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, help_text='Notes personnelles sur cette opportunite')),
                ('applied', models.BooleanField(default=False)),
                ('applied_at', models.DateTimeField(blank=True, null=True)),
                ('offer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bookmarks', to='germany_opportunities.ausbildungoffer')),
                ('scholarship', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bookmarks', to='germany_opportunities.scholarshipopportunity')),
            ],
            options={
                'verbose_name': 'Favori utilisateur',
                'ordering': ['-saved_at'],
            },
        ),
        migrations.AddIndex(
            model_name='ausbildungoffer',
            index=models.Index(fields=['is_active', 'sector'], name='germany_opp_is_acti_idx1'),
        ),
        migrations.AddIndex(
            model_name='ausbildungoffer',
            index=models.Index(fields=['is_active', 'language_req'], name='germany_opp_is_acti_idx2'),
        ),
    ]
