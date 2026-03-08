"""
Commande Django : génération audio TTS pour les leçons HÖREN de GermanPrepApp.

Utilise le service TTS existant (edge-tts DE KatjaNeural en priorité).
Génère un fichier MP3 par leçon HÖREN et sauvegarde le chemin dans GermanLesson.audio_url.

Usage :
    python manage.py generate_german_audio
    python manage.py generate_german_audio --level A1
    python manage.py generate_german_audio --exam_type GOETHE --level B1
    python manage.py generate_german_audio --force   # re-génère même si audio existe déjà
"""
import logging
import re

from django.core.management.base import BaseCommand

from GermanPrepApp.models import GermanLesson
from ai_engine.services.tts_service import generate_audio

logger = logging.getLogger(__name__)

# Répertoire de sortie relatif à MEDIA_ROOT
AUDIO_OUTPUT_DIR = "audio/german"


def _extract_audio_text(lesson: GermanLesson) -> str:
    """
    Extrait le texte à lire depuis le contenu de la leçon HÖREN.
    Prend l'intro + les 500 premiers caractères du content (sans HTML).
    """
    # Nettoyer les balises HTML
    raw = (lesson.intro or "") + "\n\n" + (lesson.content or "")
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Limiter à 1500 caractères (environ 2 min de lecture)
    if len(clean) > 1500:
        clean = clean[:1500].rsplit(" ", 1)[0]

    return clean


class Command(BaseCommand):
    help = "Génère les fichiers audio TTS pour les leçons HÖREN de GermanPrepApp"

    def add_arguments(self, parser):
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Filtrer par niveau CECR (A1, A2, B1, B2, C1, C2)",
        )
        parser.add_argument(
            "--exam_type",
            type=str,
            default=None,
            help="Filtrer par type d'examen (GOETHE, TELC, TESTDAF, DSH, GENERAL, INTEGRATION)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-générer l'audio même si un fichier existe déjà",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continuer en cas d'erreur TTS",
        )

    def handle(self, *args, **options):
        level = options["level"].upper() if options["level"] else None
        exam_type = options["exam_type"].upper() if options["exam_type"] else None
        force = options["force"]
        continue_on_error = options["continue_on_error"]

        qs = GermanLesson.objects.filter(skill="HOREN").select_related("exam")

        if level:
            qs = qs.filter(exam__level=level)
        if exam_type:
            qs = qs.filter(exam__exam_type=exam_type)

        if not force:
            qs = qs.filter(audio_url="")

        total = qs.count()
        self.stdout.write(
            f"🎙️ {total} leçon(s) HÖREN à traiter"
            + (" (force=True, re-génération)" if force else "")
        )

        done = 0
        failed = 0

        for lesson in qs:
            text = _extract_audio_text(lesson)

            if not text:
                self.stdout.write(
                    self.style.WARNING(f"  [{lesson.id}] Texte vide, ignoré.")
                )
                continue

            self.stdout.write(
                f"  [{lesson.id}] {lesson.exam.level}/{lesson.title[:50]}…", ending=" "
            )
            self.stdout.flush()

            try:
                rel_path = generate_audio(
                    text=text,
                    language="de",
                    output_dir=AUDIO_OUTPUT_DIR,
                )
                lesson.audio_url = rel_path
                lesson.save(update_fields=["audio_url"])
                done += 1
                self.stdout.write(self.style.SUCCESS(f"OK → {rel_path}"))

            except Exception as exc:
                failed += 1
                logger.warning(
                    "generate_german_audio: échec leçon %d — %s", lesson.id, exc
                )
                if continue_on_error:
                    self.stdout.write(self.style.WARNING(f"ERREUR : {exc}"))
                else:
                    self.stderr.write(f"ERREUR leçon {lesson.id} : {exc}")
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Audio terminé : {done} généré(s), {failed} échec(s)."
            )
        )
