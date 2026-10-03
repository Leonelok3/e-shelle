import datetime
from zoneinfo import ZoneInfo
from django.core.management.base import BaseCommand
from artist_hub.models import CastingSession


class Command(BaseCommand):
    help = "Initialise la session de casting par défaut pour OPLUS — Douala Fashion Week 2026."

    def add_arguments(self, parser):
        parser.add_argument(
            "--extend-registration", action="store_true",
            help="Réactive la session et aligne les inscriptions sur le casting du 14 novembre 2026.",
        )

    def handle(self, *args, **options):
        deadline = datetime.datetime(2026, 11, 13, 23, 59, 59, tzinfo=ZoneInfo("Africa/Douala"))
        session, created = CastingSession.objects.get_or_create(
            slug="douala-fashion-week-2026",
            defaults={
                "title": "Douala Fashion Week 2026",
                "subtitle": "Casting : 14 novembre 2026 · Défilé : 26 décembre 2026 — Hôtel Krystal Palace Douala",
                "description": (
                    "Recrutement officiel de mannequins Hommes et Femmes pour la prestigieuse "
                    "Fashion Week Douala 2026 présentée par OPLUS / GROUP OPUS.\n\n"
                    "• Hommes : Taille 1m83 minimum\n"
                    "• Femmes : Taille 1m75 minimum\n"
                    "• Inscription ouverte au Cameroun et à l'International. Casting gratuit."
                ),
                "casting_date": datetime.date(2026, 11, 14),
                "event_date": datetime.date(2026, 12, 26),
                "event_location": "Hôtel Krystal Palace, Douala, Cameroun",
                "fee_cameroon": 0,
                "fee_international": 0,
                "min_height_male": 183,
                "min_height_female": 175,
                "closes_at": deadline,
                "is_active": True,
            },
        )
        if options["extend_registration"]:
            session.closes_at = deadline
            session.is_active = True
            session.casting_date = datetime.date(2026, 11, 14)
            session.event_date = datetime.date(2026, 12, 26)
            session.subtitle = "Casting : 14 novembre 2026 · Défilé : 26 décembre 2026 — Hôtel Krystal Palace Douala"
            session.save(update_fields=["closes_at", "is_active", "casting_date", "event_date", "subtitle"])
            self.stdout.write(self.style.SUCCESS("Casting : 14 novembre. Défilé : 26 décembre. Inscriptions jusqu'au 13 novembre 2026 à 23:59:59 (Africa/Douala)."))
        if created:
            self.stdout.write(self.style.SUCCESS(f"Session de casting créée avec succès : {session.title}"))
        else:
            self.stdout.write(self.style.NOTICE(f"La session de casting existe déjà : {session.title}"))
