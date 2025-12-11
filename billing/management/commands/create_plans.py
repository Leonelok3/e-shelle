# billing/management/commands/create_plans.py
from django.core.management.base import BaseCommand
from billing.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Crée les plans d\'abonnement par défaut'

    def handle(self, *args, **options):
        plans_data = [
            {
                "name": "Découverte 24h",
                "slug": "decouverte-24h",
                "duration_days": 1,
                "price_usd": 2.99,
                "price_xaf": 1800,
                "is_popular": False,
                "order": 1,
                "features": [
                    "✓ Accès à toutes les applications",
                    "✓ Génération de CV illimitée",
                    "✓ Lettres de motivation IA",
                    "✓ Tests de français/anglais/allemand",
                    "✓ Assistance visa (étude, travail, tourisme)",
                    "✓ Accès 24 heures",
                ]
            },
            {
                "name": "Hebdomadaire",
                "slug": "hebdo-7j",
                "duration_days": 7,
                "price_usd": 9.99,
                "price_xaf": 6000,
                "is_popular": False,
                "order": 2,
                "features": [
                    "✓ Accès à toutes les applications",
                    "✓ Génération de CV illimitée",
                    "✓ Lettres de motivation IA",
                    "✓ Tests de français/anglais/allemand",
                    "✓ Assistance visa (étude, travail, tourisme)",
                    "✓ Suivi de candidatures",
                    "✓ Accès 7 jours",
                ]
            },
            {
                "name": "Mensuel",
                "slug": "mensuel-30j",
                "duration_days": 30,
                "price_usd": 24.99,
                "price_xaf": 15000,
                "is_popular": True,
                "order": 3,
                "features": [
                    "✓ Accès à toutes les applications",
                    "✓ Génération de CV illimitée",
                    "✓ Lettres de motivation IA",
                    "✓ Tests de français/anglais/allemand",
                    "✓ Assistance visa (étude, travail, tourisme)",
                    "✓ Suivi de candidatures",
                    "✓ Support prioritaire",
                    "✓ Accès 30 jours",
                ]
            },
            {
                "name": "Annuel",
                "slug": "annuel-365j",
                "duration_days": 365,
                "price_usd": 199.99,
                "price_xaf": 120000,
                "is_popular": False,
                "order": 4,
                "features": [
                    "✓ Accès à toutes les applications",
                    "✓ Génération de CV illimitée",
                    "✓ Lettres de motivation IA",
                    "✓ Tests de français/anglais/allemand",
                    "✓ Assistance visa (étude, travail, tourisme)",
                    "✓ Suivi de candidatures",
                    "✓ Support prioritaire VIP",
                    "✓ Mises à jour exclusives",
                    "✓ Accès 1 an complet",
                    "💰 Économisez 33% (16.67$/mois)",
                ]
            },
        ]

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.update_or_create(
                slug=plan_data["slug"],
                defaults=plan_data
            )
            
            action = "créé" if created else "mis à jour"
            self.stdout.write(
                self.style.SUCCESS(f"✓ Plan '{plan.name}' {action}")
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ {len(plans_data)} plans créés avec succès !")
        )