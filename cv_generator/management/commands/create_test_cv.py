# Créer ce fichier dans: cv_generator/management/commands/init_cv.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cv_generator.models import CV, CVTemplate

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
            self.stdout.write(self.style.ERROR(f'Utilisateur "{username}" introuvable'))
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
            f'✅ CV créé avec succès (ID: {cv.id}) pour {username}'
        ))
        self.stdout.write(
            f'🔗 URL: /cv-generator/cv/{cv.id}/create/'
        )


# Commande pour créer des templates de base
class Command2(BaseCommand):
    help = 'Crée des templates de CV de base'

    def handle(self, *args, **options):
        templates_data = [
            {
                'name': 'Professionnel Moderne',
                'description': 'Template élégant pour secteurs corporate',
                'industry': 'Tous secteurs',
                'country': 'International',
                'style_type': 'professional',
                'popularity_score': 100,
                'html_template': '<div>Template professionnel</div>'
            },
            {
                'name': 'Créatif Design',
                'description': 'Pour designers, artistes et créatifs',
                'industry': 'Design & Arts',
                'country': 'International',
                'style_type': 'creative',
                'popularity_score': 85,
                'html_template': '<div>Template créatif</div>'
            },
            {
                'name': 'Canadien Standard',
                'description': 'Conforme aux standards canadiens',
                'industry': 'Tous secteurs',
                'country': 'Canada',
                'style_type': 'canadian',
                'popularity_score': 90,
                'html_template': '<div>Template canadien</div>'
            },
        ]
        
        for template_data in templates_data:
            CVTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ {len(templates_data)} templates créés/vérifiés'
        ))