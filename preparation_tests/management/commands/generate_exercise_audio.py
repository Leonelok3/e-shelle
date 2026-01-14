from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import subprocess
import uuid

from preparation_tests.models import CourseExercise, Asset


class Command(BaseCommand):
    help = "Génère les audios TTS pour les exercices sans audio"

    def handle(self, *args, **options):
        exercises = CourseExercise.objects.filter(audio__isnull=True)

        if not exercises.exists():
            self.stdout.write(self.style.SUCCESS("✅ Aucun exercice à traiter"))
            return

        audio_dir = Path(settings.MEDIA_ROOT) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        model_path = Path(settings.BASE_DIR) / "tts_engine/voices/fr_FR-upmc-medium.onnx"

        for ex in exercises:
            text = ex.question_text.strip()
            if not text:
                continue

            filename = f"exercise_{ex.id}_{uuid.uuid4().hex}.wav"
            output_path = audio_dir / filename

            cmd = [
                "piper",
                "--model", str(model_path),
                "--output_file", str(output_path),
                "--sentence-silence", "0.6",
                "--length-scale", "1.05",
                "--noise-scale", "0.6",
                "--noise-w-scale", "0.8",
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            process.communicate(text)

            asset = Asset.objects.create(
                kind="audio",
                file=f"audio/{filename}",
                lang="fr",
            )

            ex.audio = asset
            ex.save()

            self.stdout.write(
                self.style.SUCCESS(f"🎧 Audio généré pour exercice #{ex.id}")
            )
