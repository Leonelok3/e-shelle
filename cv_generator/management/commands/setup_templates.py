from django.core.management.base import BaseCommand
from cv_generator.models import CVTemplate

class Command(BaseCommand):
    help = 'Initialiser les templates de CV par défaut'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Canada ATS',
                'slug': 'canada-ats',
                'description': 'Template optimisé pour les systèmes ATS canadiens',
                'category': 'ats',
                'template_file': 'cv_canada_ats.html',
                'is_premium': False,
                'supports_colors': False,
                'supports_photo': False,
                'order': 1,
            },
            {
                'name': 'Modern Creative',
                'slug': 'modern-creative',
                'description': 'Design moderne avec couleurs personnalisables',
                'category': 'creative',
                'template_file': 'cv_modern_creative.html',
                'is_premium': True,
                'supports_colors': True,
                'supports_photo': True,
                'order': 2,
            },
            {
                'name': 'Executive Classic',
                'slug': 'executive-classic',
                'description': 'Style professionnel pour cadres supérieurs',
                'category': 'professional',
                'template_file': 'cv_executive_classic.html',
                'is_premium': True,
                'supports_colors': False,
                'supports_photo': True,
                'order': 3,
            },
            {
                'name': 'Tech Minimal',
                'slug': 'tech-minimal',
                'description': 'Design épuré pour développeurs et tech',
                'category': 'modern',
                'template_file': 'cv_tech_minimal.html',
                'is_premium': False,
                'supports_colors': True,
                'supports_photo': False,
                'order': 4,
            },
        ]
        
        for tpl_data in templates:
            CVTemplate.objects.update_or_create(
                slug=tpl_data['slug'],
                defaults=tpl_data
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Template "{tpl_data["name"]}" créé/mis à jour')
            )
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 {len(templates)} templates initialisés'))

