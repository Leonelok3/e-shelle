import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from artist_hub.models import CastingSession


class Command(BaseCommand):
    help = "Initialise la session de casting par défaut pour OPLUS — Douala Fashion Week 2026."

    def handle(self, *args, **options):
        session, created = CastingSession.objects.get_or_create(
            slug="douala-fashion-week-2026",
            defaults={
                "title": "Douala Fashion Week 2026",
                "subtitle": "Samedi 26 Décembre 2026 — Hôtel Krystal Palace Douala",
                "description": (
                    "Recrutement officiel de mannequins Hommes et Femmes pour la prestigieuse "
                    "Fashion Week Douala 2026 présentée par OPLUS / GROUP OPUS.\n\n"
                    "• Hommes : Taille 1m83 minimum\n"
                    "• Femmes : Taille 1m75 minimum\n"
                    "• Inscription ouverte au Cameroun (3 000 FCFA) et à l'International (5 000 FCFA)."
                ),
                "event_date": datetime.date(2026, 12, 26),
                "event_location": "Hôtel Krystal Palace, Douala, Cameroun",
                "fee_cameroon": 3000,
                "fee_international": 5000,
                "min_height_male": 183,
                "min_height_female": 175,
                "closes_at": timezone.make_aware(
                    datetime.datetime(2026, 9, 28, 23, 59, 59)
                ),
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Session de casting créée avec succès : {session.title}"))
        else:
            self.stdout.write(self.style.NOTICE(f"La session de casting existe déjà : {session.title}"))
