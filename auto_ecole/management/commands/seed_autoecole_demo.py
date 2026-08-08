from django.core.management.base import BaseCommand
from django.utils.text import slugify

from auto_ecole.models import DrivingSchool, Course


class Command(BaseCommand):
    help = "Seed demo DrivingSchool and Course data for auto_ecole"

    def handle(self, *args, **options):
        schools = [
            {
                "name": "Auto-école Centrale",
                "city": "Yaoundé",
                "description": "Cours théoriques et pratiques - moniteurs expérimentés.",
                "phone": "+237650000001",
                "latitude": 3.8520,
                "longitude": 11.5021,
            },
            {
                "name": "Académie Permis Pro",
                "city": "Douala",
                "description": "Préparation examen code de la route et conduite accompagnée.",
                "phone": "+237650000002",
                "latitude": 4.0470,
                "longitude": 9.7679,
            },
        ]

        created = 0
        for s in schools:
            slug = slugify(s["name"])[:200]
            school, was_created = DrivingSchool.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": s["name"],
                    "city": s["city"],
                    "description": s["description"],
                    "phone": s["phone"],
                    "latitude": s.get("latitude"),
                    "longitude": s.get("longitude"),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

            # Create sample courses for each school
            existing = Course.objects.filter(school=school).count()
            if existing == 0:
                Course.objects.create(
                    school=school,
                    title="Code de la route - Bases",
                    slug="code-bases",
                    summary="Principes de base du code de la route, priorités et panneaux.",
                    content="Contenu pédagogique introductif sur le code de la route.",
                    order=1,
                    is_published=True,
                )
                Course.objects.create(
                    school=school,
                    title="Sécurité et prévention",
                    slug="securite-prevention",
                    summary="Comportements sûrs au volant, prévention des risques.",
                    content="Conseils et bonnes pratiques pour conduire en sécurité.",
                    order=2,
                    is_published=True,
                )
                Course.objects.create(
                    school=school,
                    title="Manoeuvres et stationnement",
                    slug="manoeuvres-stationnement",
                    summary="Techniques de stationnement et manoeuvres de base.",
                    content="Exercices pratiques et explications détaillées.",
                    order=3,
                    is_published=True,
                )

        self.stdout.write(self.style.SUCCESS(f"Seed completed. Created {created} DrivingSchool(s) and sample courses."))
