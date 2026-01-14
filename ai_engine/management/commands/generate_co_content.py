import time
from django.core.management.base import BaseCommand
from ai_engine.agents.co_agent import generate_co_content
from ai_engine.services.tts_service import generate_audio
from ai_engine.services.insertion_service import insert_co_content

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

class Command(BaseCommand):
    help = "Génère automatiquement le contenu CO"

    def add_arguments(self, parser):
        parser.add_argument("--exam_id", type=int, required=True)
        parser.add_argument("--language", type=str, required=True)
        parser.add_argument("--lessons", type=int, default=1)

    def handle(self, *args, **options):
        for level in LEVELS:
            for _ in range(options["lessons"]):
                data = generate_co_content(options["language"], level)
                audio_path = generate_audio(data["audio_script"], options["language"])
                insert_co_content(
                    options["exam_id"],
                    level,
                    options["language"],
                    data,
                    audio_path
                )
                time.sleep(3)


from django.core.management.base import BaseCommand
from preparation_tests.services.tts_service import generate_audio

class Command(BaseCommand):
    help = "Génère le contenu IA + audio pour les tests de langue"

    def add_arguments(self, parser):
        parser.add_argument("--language", type=str, default="fr")

    def handle(self, *args, **options):
        audio = generate_audio(
            "Bienvenue sur Immigration97, préparation linguistique.",
            options["language"]
        )
        self.stdout.write(self.style.SUCCESS(f"Audio généré : {audio}"))
