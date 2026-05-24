from django.core.management.base import BaseCommand

from business.models import BusinessProfile, ProviderPlan


class Command(BaseCommand):
    help = "Cree les plans prestataires E-Shelle par defaut."

    def handle(self, *args, **options):
        plans = [
            {
                "code": "free",
                "name": "Gratuit",
                "plan_level": BusinessProfile.Plan.FREE,
                "monthly_price_xaf": 0,
                "duration_days": 30,
                "included_boost_days": 0,
                "included_ai_credits": 0,
                "order": 0,
                "description": "Fiche basique, visibilite limitee, commandes WhatsApp.",
            },
            {
                "code": "pro",
                "name": "Pro",
                "plan_level": BusinessProfile.Plan.PRO,
                "monthly_price_xaf": 5000,
                "duration_days": 30,
                "included_boost_days": 0,
                "included_ai_credits": 5,
                "order": 10,
                "description": "Fiche complete, badge, statistiques simples, 5 credits IA.",
            },
            {
                "code": "business",
                "name": "Business",
                "plan_level": BusinessProfile.Plan.BUSINESS,
                "monthly_price_xaf": 15000,
                "duration_days": 30,
                "included_boost_days": 7,
                "included_ai_credits": 20,
                "order": 20,
                "description": "Meilleur classement, 7 jours de boost, demandes recues, 20 credits IA.",
            },
            {
                "code": "premium",
                "name": "Premium",
                "plan_level": BusinessProfile.Plan.PREMIUM,
                "monthly_price_xaf": 30000,
                "duration_days": 30,
                "included_boost_days": 15,
                "included_ai_credits": 50,
                "order": 30,
                "description": "Top resultats IA, boost prioritaire, accompagnement, 50 credits IA.",
            },
        ]
        created = 0
        for data in plans:
            _, was_created = ProviderPlan.objects.update_or_create(
                code=data["code"],
                defaults=data,
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Plans business prets: {created} nouveau(x)."))
