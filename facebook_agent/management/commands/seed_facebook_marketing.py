from django.core.management.base import BaseCommand

from facebook_agent.models import ContentRule


RULES = [
    ("general", "inspirant", "19:00", "Vision E-Shelle: super-app africaine, IA, services locaux, Douala d'abord."),
    ("chat_ai", "dynamique", "08:30,20:30", "Créer des mini-histoires virales façon Reels/TikTok: problème quotidien + chat E-Shelle + solution."),
    ("business", "professionnel", "09:30,18:30", "Recruter prestataires et commerciaux: fiche, WhatsApp, boost, abonnement, commissions."),
    ("gaz", "dynamique", "07:00,17:30,21:00", "Focus Douala, Bonamoussadi, Akwa, Makepe: urgence gaz, livraison, WhatsApp."),
    ("resto", "amical", "11:30,18:00", "Donner envie de commander, découvrir un maquis, trouver un restaurant proche."),
    ("pressing", "amical", "07:45,16:30", "Vie urbaine, linge propre, pressing proche, collecte et livraison."),
    ("sante", "informatif", "10:00,19:30", "Rester prudent: orienter vers pharmacies et professionnels, pas de diagnostic."),
    ("jobs", "inspirant", "08:00,15:00", "Stages, emplois, missions freelance, opportunités locales."),
    ("promo", "dynamique", "12:00", "Offres, boosts, avantages prestataires, urgence légère."),
    ("rencontres", "romantique", "20:00", "Rencontres sérieuses, respect, profils vérifiés, ton positif."),
    ("njangi", "informatif", "18:00", "Tontine digitale, entraide, épargne communautaire."),
]


class Command(BaseCommand):
    help = "Initialise les règles marketing Facebook/TikTok/Reels pour E-Shelle."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for section, tone, hours, instructions in RULES:
            _, was_created = ContentRule.objects.update_or_create(
                section=section,
                defaults={
                    "is_active": True,
                    "tone": tone,
                    "post_frequency_per_day": len([h for h in hours.split(",") if h.strip()]),
                    "preferred_hours": hours,
                    "custom_instructions": instructions,
                    "include_emoji": True,
                    "include_hashtags": True,
                    "max_post_length": 700,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Règles marketing prêtes: {created} créées, {updated} mises à jour."))
