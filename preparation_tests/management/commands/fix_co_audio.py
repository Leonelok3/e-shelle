"""Generate from dedicated exercise scripts by default.

The historical shared lesson audio requires --legacy-lesson-script and a human
check that content_html contains only the listening document, not methodology.
Existing audio references are preserved by the default mode.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from ai_engine.services.tts_service import generate_audio
from preparation_tests.models import Asset, CourseLesson
from preparation_tests.services.listening_material import spoken_text


def _strip_html(html: str) -> str:
    """Supprime les balises HTML et nettoie les espaces."""
    return spoken_text(html)


def _is_valid_audio_script(text: str) -> bool:
    """
    Vérifie que le texte est un vrai script audio (pas juste une instruction).
    Un script audio valide a au moins 40 mots.
    """
    words = text.split()
    return len(words) >= 40


class Command(BaseCommand):
    help = "Génère les audios CO depuis les scripts dédiés, sans lire les consignes"

    def add_arguments(self, parser):
        parser.add_argument("--legacy-lesson-script", action="store_true", help="Lecture du cours uniquement si vérifié comme script sonore")
        parser.add_argument("--level", type=str, default="", help="Niveau CECR (A1, A2, B1…). Vide = tous.")
        parser.add_argument("--language", type=str, default="fr")
        parser.add_argument("--limit", type=int, default=0, help="Nombre max de leçons à traiter (0 = toutes)")
        parser.add_argument("--dry-run", action="store_true", help="Simulation sans écriture en base")
        parser.add_argument("--skip-existing", action="store_true",
                            help="Passer les leçons dont tous les exercices ont déjà un audio partagé")

    def handle(self, *args, **options):
        if not options["legacy_lesson_script"]:
            from django.core.management import call_command
            call_command("generate_exercise_audio", section="co", levels=options["level"],
                         language=options["language"], limit=options["limit"],
                         dry_run=options["dry_run"], stdout=self.stdout, stderr=self.stderr)
            return
        level = (options["level"] or "").strip().upper()
        language = (options["language"] or "fr").strip().lower()
        limit = int(options["limit"] or 0)
        dry_run = bool(options["dry_run"])
        skip_existing = bool(options["skip_existing"])

        qs = CourseLesson.objects.filter(section="co", is_published=True).prefetch_related("exercises")
        if level:
            qs = qs.filter(level=level)
        qs = qs.order_by("level", "order")
        if limit > 0:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"[fix_co_audio] {total} leçons CO à traiter (dry_run={dry_run})")

        ok = skipped = failed = 0

        for lesson in qs:
            exercises = list(lesson.exercises.filter(is_active=True))
            if not exercises:
                self.stdout.write(self.style.WARNING(f"  [skip] leçon#{lesson.pk} '{lesson.title}': aucun exercice actif"))
                skipped += 1
                continue

            # Option: passer si tous les exercices partagent déjà le même audio
            if skip_existing:
                audio_ids = {ex.audio_id for ex in exercises if ex.audio_id}
                if len(audio_ids) == 1 and all(ex.audio_id for ex in exercises):
                    self.stdout.write(f"  [skip] leçon#{lesson.pk}: audio partagé déjà présent")
                    skipped += 1
                    continue

            # Extraire le texte du script audio depuis content_html
            raw_content = lesson.content_html or ""
            script_text = _strip_html(raw_content)

            if not _is_valid_audio_script(script_text):
                self.stdout.write(self.style.WARNING(
                    f"  [skip] leçon#{lesson.pk} '{lesson.title}': script trop court ({len(script_text.split())} mots)"
                ))
                skipped += 1
                continue

            self.stdout.write(f"  [TTS] leçon#{lesson.pk} '{lesson.title}' ({len(script_text.split())} mots)…")

            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"       → [DRY-RUN] audio non généré"))
                ok += 1
                continue

            try:
                rel_audio_path = generate_audio(script_text, language=language)

                if not rel_audio_path:
                    raise ValueError("generate_audio a retourné un chemin vide")

                # Créer un Asset audio unique pour cette leçon
                audio_asset = Asset.objects.create(kind="audio", lang=language)
                audio_asset.file = rel_audio_path
                audio_asset.save(update_fields=["file"])

                # Assigner cet audio à TOUS les exercices de la leçon
                lesson.exercises.filter(is_active=True).update(audio=audio_asset)

                self.stdout.write(self.style.SUCCESS(
                    f"       → asset#{audio_asset.pk} créé, {len(exercises)} exercices mis à jour"
                ))
                ok += 1

            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  [ERREUR] leçon#{lesson.pk}: {exc}"))
                failed += 1

        self.stdout.write("")
        self.stdout.write(f"[fix_co_audio] Terminé : {ok} OK · {skipped} ignorées · {failed} erreurs")
