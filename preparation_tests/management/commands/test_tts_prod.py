from django.core.management.base import BaseCommand
from preparation_tests.services.tts_bridge import generate_audio

class Command(BaseCommand):
    help = "Test TTS en production (génère un audio réel)"

    def handle(self, *args, **options):
        audio_path = generate_audio(
            "Ceci est un test officiel du moteur audio en production pour Immigration97.",
            "fr"
        )
        self.stdout.write(self.style.SUCCESS(f"AUDIO GÉNÉRÉ : {audio_path}"))
