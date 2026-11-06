from django.core.management.base import BaseCommand

from business.models import BusinessProfile, ProviderPlan


# Prix mis à jour 8 oct 2026 pour Tech Provider - Audit safe
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
                "name": "Présence — Pro",
                "plan_level": BusinessProfile.Plan.PRO,
                "monthly_price_xaf": 5000,
                "duration_days": 30,
                "included_boost_days": 0,
                "included_ai_credits": 5,
                "order": 10,
                "description": "Fiche publique optimisée pour la visibilité locale, catalogue jusqu'à 20 articles, partage, 5 crédits IA, connexion WhatsApp et CRM de contacts avec réponses dans la fenêtre de 24 h.",
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
                "description": "Avantages Pro, visibilité prioritaire E-Shelle avec 7 jours de boost, jusqu'à 50 articles, vidéo au catalogue, 20 crédits IA, synchronisation du catalogue Meta et relances CRM individuelles sous réserve d'activation, de modèles approuvés et du consentement explicite.",
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
                "description": "Avantages Business, catalogue sans plafond déclaré dans le code, vidéo au catalogue, 15 jours de boost E-Shelle, 50 crédits IA et outils de visibilité locale. Aucun classement Google ou placement dans un assistant IA n'est garanti; accompagnement humain sur devis.",
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
