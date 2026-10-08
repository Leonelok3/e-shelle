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
                "description": "Fiche basique et contact WhatsApp public. Le WhatsApp CRM n'est pas inclus.",
            },
            {
                "code": "pro",
                "name": "Fiche Business Premium",
                "plan_level": BusinessProfile.Plan.PRO,
                "monthly_price_xaf": 5000,
                "duration_days": 30,
                "included_boost_days": 0,
                "included_ai_credits": 5,
                "order": 10,
                "description": "Fiche et catalogue publics, partage, 5 crédits IA, connexion WhatsApp et CRM de contacts avec réponses dans la fenêtre de 24 h.",
            },
            {
                "code": "business",
                "name": "Business",
                "plan_level": BusinessProfile.Plan.BUSINESS,
                "monthly_price_xaf": 10000,
                "duration_days": 30,
                "included_boost_days": 7,
                "included_ai_credits": 20,
                "order": 20,
                "description": "Avantages Pro, meilleur classement, 7 jours de boost, demandes reçues, 20 crédits IA, synchronisation du catalogue et relances CRM individuelles par modèles Meta approuvés avec consentement explicite.",
            },
            {
                "code": "premium",
                "name": "Premium",
                "plan_level": BusinessProfile.Plan.PREMIUM,
                "monthly_price_xaf": 25000,
                "duration_days": 30,
                "included_boost_days": 15,
                "included_ai_credits": 50,
                "order": 30,
                "description": "Avantages Business, top résultats IA, carrousels premium, accompagnement marketing, 50 crédits IA et relances CRM individuelles par modèles Meta approuvés avec consentement explicite.",
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
