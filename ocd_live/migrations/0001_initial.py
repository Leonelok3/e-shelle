from decimal import Decimal
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OpportunityCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Nom de la catégorie')),
                ('slug', models.SlugField(max_length=140, unique=True)),
                ('icon', models.CharField(default='💼', help_text='Emoji ou icône représentative', max_length=30)),
                ('order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': "Catégorie d'opportunité",
                'verbose_name_plural': "Catégories d'opportunités",
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LiveSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=240, verbose_name='Titre de la session Live')),
                ('slug', models.SlugField(max_length=260, unique=True)),
                ('subtitle', models.CharField(blank=True, max_length=300, verbose_name='Sous-titre explicite')),
                ('description', models.TextField(verbose_name="Programme détaillé de l'intervention")),
                ('speaker_name', models.CharField(max_length=150, verbose_name='Intervenant / Expert terrain')),
                ('speaker_title', models.CharField(max_length=200, verbose_name="Titre / Spécialité de l'intervenant")),
                ('speaker_avatar', models.ImageField(blank=True, null=True, upload_to='ocd_live/speakers/', verbose_name="Photo de l'expert")),
                ('scheduled_at', models.DateTimeField(verbose_name='Date et heure de début')),
                ('duration_minutes', models.PositiveIntegerField(default=90, verbose_name='Durée estimée (minutes)')),
                ('stream_provider', models.CharField(choices=[('YOUTUBE', 'YouTube Live'), ('VIMEO', 'Vimeo Live'), ('JITSI', 'Salon Privé Visioconférence'), ('CUSTOM', 'Flux RTMP / HLS Direct')], default='YOUTUBE', max_length=20, verbose_name='Diffuseur')),
                ('stream_url', models.CharField(blank=True, help_text='URL YouTube Live, Vimeo ou salon visio sécurisé', max_length=500, verbose_name='Lien / ID du flux de diffusion')),
                ('access_tier', models.CharField(choices=[('FREE', 'Gratuit (Inscription libre)'), ('PASS_REQUIRED', 'Pass Membre ou Ticket Unitaire'), ('VIP_ONLY', 'Pass VIP Investisseur Uniquement')], default='PASS_REQUIRED', max_length=20, verbose_name="Niveau d'accès")),
                ('ticket_price_xaf', models.DecimalField(decimal_places=2, default=Decimal('2500.00'), help_text='0 si réservé uniquement aux abonnés ou gratuit', max_digits=10, verbose_name='Prix du ticket unitaire (FCFA)')),
                ('is_live_now', models.BooleanField(default=False, verbose_name='🔴 En direct maintenant')),
                ('is_completed', models.BooleanField(default=False, verbose_name='Session terminée')),
                ('replay_url', models.URLField(blank=True, verbose_name='Lien du Replay officiel')),
                ('banner_image', models.ImageField(blank=True, null=True, upload_to='ocd_live/banners/', verbose_name="Bannière d'annonce")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Session Live / Masterclass',
                'verbose_name_plural': 'Sessions Live / Masterclasses',
                'ordering': ['-is_live_now', 'scheduled_at'],
            },
        ),
        migrations.CreateModel(
            name='OCDPackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Nom du Pass')),
                ('slug', models.SlugField(max_length=170, unique=True)),
                ('code', models.CharField(help_text='Ex: pass_unitaire, pass_mensuel, pass_vip', max_length=50, unique=True)),
                ('price_xaf', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Prix (FCFA)')),
                ('duration_days', models.PositiveIntegerField(default=30, verbose_name='Durée de validité (jours)')),
                ('can_access_all_lives', models.BooleanField(default=True, verbose_name='Accès illimité à tous les Lives & Replays')),
                ('private_coaching_credits', models.PositiveIntegerField(default=0, verbose_name='Nombre de sessions 1-to-1 incluses')),
                ('full_opportunities_dossier', models.BooleanField(default=True, verbose_name="Accès aux fiches d'audit détaillées des opportunités")),
                ('description', models.TextField(verbose_name='Avantages inclus (1 par ligne)')),
                ('is_popular', models.BooleanField(default=False, verbose_name="Badge 'Plus Populaire'")),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif à la vente')),
                ('order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Formule / Pass OCD',
                'verbose_name_plural': 'Formules & Pass OCD',
                'ordering': ['order', 'price_xaf'],
            },
        ),
        migrations.CreateModel(
            name='Opportunity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220, verbose_name="Titre de l'opportunité")),
                ('slug', models.SlugField(max_length=250, unique=True)),
                ('country', models.CharField(default='Cameroun', max_length=100, verbose_name='Pays')),
                ('city', models.CharField(blank=True, max_length=120, verbose_name='Ville / Région')),
                ('summary', models.TextField(help_text='Les points clés en 2-3 phrases percutantes', max_length=500, verbose_name='Résumé percutant')),
                ('full_description', models.TextField(verbose_name='Dossier & Cahier des charges complet')),
                ('min_capital_xaf', models.DecimalField(decimal_places=2, default=Decimal('500000.00'), max_digits=12, verbose_name="Ticket d'entrée / Capital minimum (FCFA)")),
                ('estimated_roi', models.CharField(default='25% - 40% / an', max_length=100, verbose_name='Rentabilité estimée')),
                ('timeframe', models.CharField(default='6 à 12 mois', max_length=100, verbose_name="Horizon d'investissement")),
                ('risk_level', models.CharField(choices=[('LOW', 'Faible (Marché stable & sécurisé)'), ('MODERATE', 'Modéré (Rendement attractif)'), ('HIGH', 'Élevé (Fort potentiel / Venture)')], default='MODERATE', max_length=20, verbose_name='Niveau de risque')),
                ('status', models.CharField(choices=[('VERIFIED', 'Vérifiée & Auditée'), ('IN_PROGRESS', 'Ouverte aux partenaires'), ('FUNDED', 'Complétée / Financée'), ('ARCHIVED', 'Archivée')], default='VERIFIED', max_length=20, verbose_name='Statut')),
                ('pitch_video_url', models.URLField(blank=True, verbose_name='Lien vidéo de présentation (YouTube / Drive)')),
                ('whatsapp_contact', models.CharField(default='+237680625082', max_length=30, verbose_name='WhatsApp direct du référent terrain')),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='ocd_live/opportunities/', verbose_name='Photo de couverture')),
                ('is_featured', models.BooleanField(default=False, verbose_name="Mettre en avant sur la page d'accueil")),
                ('views_count', models.PositiveIntegerField(default=0, verbose_name='Nombre de consultations')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='opportunities', to='ocd_live.opportunitycategory', verbose_name='Catégorie')),
            ],
            options={
                'verbose_name': "Opportunité d'affaires",
                'verbose_name_plural': "Opportunités d'affaires",
                'ordering': ['-is_featured', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Slot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default="Session d'orientation Opportunité Terrain", max_length=180)),
                ('expert_name', models.CharField(default='Expert Référent OCD Live', max_length=120)),
                ('start_time', models.DateTimeField(verbose_name='Date & Heure de début')),
                ('end_time', models.DateTimeField(verbose_name='Date & Heure de fin')),
                ('capacity', models.PositiveIntegerField(default=1, verbose_name='Capacité maximale (places)')),
                ('booked_count', models.PositiveIntegerField(default=0, verbose_name='Nombre de places réservées')),
                ('price_xaf', models.DecimalField(decimal_places=2, default=Decimal('10000.00'), max_digits=10, verbose_name='Prix (FCFA)')),
                ('is_active', models.BooleanField(default=True)),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='slots', to='ocd_live.livesession', verbose_name='Session Live liée (optionnel)')),
            ],
            options={
                'verbose_name': 'Créneau de réservation',
                'verbose_name_plural': 'Créneaux de réservation',
                'ordering': ['start_time'],
            },
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_code', models.CharField(editable=False, max_length=32, unique=True)),
                ('status', models.CharField(choices=[('PENDING', 'En attente de paiement'), ('CONFIRMED', 'Confirmé & Validé'), ('CANCELLED', 'Annulé')], default='PENDING', max_length=20, verbose_name='Statut')),
                ('amount_paid', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('whatsapp_number', models.CharField(blank=True, max_length=30, verbose_name='WhatsApp pour notifications')),
                ('transaction_ref', models.CharField(blank=True, max_length=60, verbose_name='Référence Transaction E-Shelle')),
                ('whatsapp_reminder_sent', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('package', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookings', to='ocd_live.ocdpackage', verbose_name='Pass souscrit')),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookings', to='ocd_live.livesession', verbose_name='Session Live')),
                ('slot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookings', to='ocd_live.slot', verbose_name='Créneau réservé')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ocd_bookings', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur')),
            ],
            options={
                'verbose_name': 'Réservation / Ticket OCD Live',
                'verbose_name_plural': 'Réservations / Tickets OCD Live',
                'ordering': ['-created_at'],
            },
        ),
    ]

