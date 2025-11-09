# Fichier: cv_generator/management/commands/init_cv.py
# Ce fichier doit contenir UNIQUEMENT ce code Python

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cv_generator.models import CV

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialise un CV de démarrage pour un utilisateur'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nom d\'utilisateur')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'❌ Utilisateur "{username}" introuvable.'
            ))
            self.stdout.write(self.style.WARNING(
                'Créez d\'abord un utilisateur avec: python manage.py createsuperuser'
            ))
            self.stdout.write('\nUtilisateurs disponibles:')
            for u in User.objects.all():
                self.stdout.write(f'  - {u.username}')
            return
        
        # Vérifier si l'utilisateur a déjà un CV
        existing_cv = CV.objects.filter(utilisateur=user).first()
        if existing_cv:
            self.stdout.write(self.style.WARNING(
                f'⚠️ Cet utilisateur a déjà un CV (ID: {existing_cv.id})'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'🔗 Accédez-y via: http://127.0.0.1:8000/cv-generator/cv/{existing_cv.id}/create/'
            ))
            return
        
        # Créer un CV vide
        cv = CV.objects.create(
            utilisateur=user,
            profession="",
            pays_cible="",
            data={
                "personal_info": {
                    "nom": "",
                    "prenom": "",
                    "email": user.email,
                    "telephone": ""
                }
            },
            current_step=1
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ CV créé avec succès pour {username}!'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'📋 ID du CV: {cv.id}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'🔗 Accédez-y via: http://127.0.0.1:8000/cv-generator/cv/{cv.id}/create/'
        ))
        self.stdout.write('')