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
                "duration_days": 14,
                "included_boost_days": 0,
                "included_ai_credits": 0,
                "order": 0,
                "description": "Fiche Business avec jusqu'à 5 produits avec photos. Visibilité pendant 14 jours, puis fiche en pause sans suppression des données. Sans crédits IA, WABA, agent IA, boost ni tableau de bord avancé.",
            },
            {
                "code": "pro",
                "name": "Présence — Pro",
                "plan_level": BusinessProfile.Plan.PRO,
                "monthly_price_xaf": 5000,
                "duration_days": 30,
                "included_boost_days": 5,
                "included_ai_credits": 5,
                "order": 10,
                "description": "Tout Gratuit, jusqu'à 20 produits, visibilité sur e-shelle.com, référencement Google et visibilité dans E-Shelle AI/LLM sans garantie de classement, tableau de bord commerçant, 5 crédits IA et 5 jours de boost. Sans WABA ni agent IA de réponse.",
            },
            {
                "code": "business",
                "name": "Croissance — Business",
                "plan_level": BusinessProfile.Plan.BUSINESS,
                "monthly_price_xaf": 15000,
                "duration_days": 30,
                "included_boost_days": 7,
                "included_ai_credits": 20,
                "order": 20,
                "description": "Tout Présence — Pro, jusqu'à 50 produits, connexion WABA (selon éligibilité et validations Meta), agent IA de réponse limité par les crédits, 20 crédits IA, 7 jours de boost, assistance et formation. Donne le droit de demander l'activation de la Business Key, qui reste une activation séparée à 9 900 FCFA.",
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
