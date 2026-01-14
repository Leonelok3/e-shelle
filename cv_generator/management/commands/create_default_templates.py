# cv_generator/management/commands/create_default_templates.py

from django.core.management.base import BaseCommand
from cv_generator.models import CVTemplate


class Command(BaseCommand):
    help = 'Cree les templates de CV par defaut'

    def handle(self, *args, **kwargs):
        templates_data = [
            {
                'name': 'Canada ATS Optimise',
                'description': 'Template optimise pour les systemes ATS canadiens. Format sobre et professionnel.',
                'template_file': 'cv_canada_ats.html',
                'is_active': True,
                'is_premium': False,
                'order': 1,
            },
            {
                'name': 'Europe Moderne',
                'description': 'Design moderne adapte au marche europeen. Mise en page elegante avec sections claires.',
                'template_file': 'cv_europe.html',
                'is_active': True,
                'is_premium': False,
                'order': 2,
            },
            {
                'name': 'USA Professionnel',
                'description': 'Format americain classique. Parfait pour les candidatures corporate.',
                'template_file': 'cv_professional.html',
                'is_active': True,
                'is_premium': False,
                'order': 3,
            },
            {
                'name': 'Tech Modern (Premium)',
                'description': 'Design moderne pour les profils tech. Couleurs vives et sections innovantes.',
                'template_file': 'cv_modern.html',
                'is_active': True,
                'is_premium': True,
                'order': 4,
            },
            {
                'name': 'Executive (Premium)',
                'description': 'Template haut de gamme pour cadres superieurs. Elegance et sophistication.',
                'template_file': 'cv_executive.html',
                'is_active': True,
                'is_premium': True,
                'order': 5,
            },
        ]

        created_count = 0
        updated_count = 0

        self.stdout.write('=' * 60)
        self.stdout.write(self.style.HTTP_INFO(' CREATION DES TEMPLATES DE CV '))
        self.stdout.write('=' * 60)
        self.stdout.write('')

        for data in templates_data:
            template, created = CVTemplate.objects.update_or_create(
                name=data['name'],
                defaults=data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  [+] CREE    : {template.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  [~] UPDATE  : {template.name}')
                )

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'  TERMINE : {created_count} crees | {updated_count} mis a jour'
            )
        )
        self.stdout.write('=' * 60)
        self.stdout.write('')
        
        # Verification finale
        total = CVTemplate.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.HTTP_INFO(f'  Total templates actifs en base : {total}')
        )
        self.stdout.write('')