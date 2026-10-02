from django.core.management.base import BaseCommand, CommandError
from ai_engine.services.tts_service import generate_audio
from preparation_tests.services.daily_tcf_bank import TOPICS


class Command(BaseCommand):
    help = "Prépare les sept documents audio originaux du cycle quotidien TCF (cache réutilisé)."

    def handle(self, *args, **options):
        failures = 0
        for topic in TOPICS:
            try:
                path = generate_audio(topic["co"]["document"], language="fr", output_dir="audio/fr/tcf_daily")
                self.stdout.write(f"OK : {topic['title']} -> {path}")
            except Exception as error:
                failures += 1
                self.stderr.write(f"Échec audio : {topic['title']} ({type(error).__name__})")
        if failures:
            raise CommandError(f"{failures} audio(s) quotidien(s) non préparé(s).")
