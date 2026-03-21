"""
Commande : fix_co_audio
=======================
Pour chaque leçon CO, génère UN seul audio TTS depuis lesson.content_html
(le vrai script audio) et l'assigne à tous les exercices de la leçon.

Usage :
    python manage.py fix_co_audio                   # tous niveaux
    python manage.py fix_co_audio --level B1        # un seul niveau
    python manage.py fix_co_audio --dry-run         # simulation sans écriture
    python manage.py fix_co_audio --limit 5         # 5 leçons max (test)
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from ai_engine.services.tts_service import generate_audio
from preparation_tests.models import Asset, CourseLesson


def _strip_html(html: str) -> str:
    """Supprime les balises HTML et nettoie les espaces."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_valid_audio_script(text: str) -> bool:
    """
    Vérifie que le texte est un vrai script audio (pas juste une instruction).
    Un script audio valide a au moins 40 mots.
    """
    words = text.split()
    return len(words) >= 40


class Command(BaseCommand):
    help = "Régénère l'audio CO depuis lesson.content_html (le vrai script audio)"

    def add_arguments(self, parser):
        parser.add_argument("--level", type=str, default="", help="Niveau CECR (A1, A2, B1…). Vide = tous.")
        parser.add_argument("--language", type=str, default="fr")
        parser.add_argument("--limit", type=int, default=0, help="Nombre max de leçons à traiter (0 = toutes)")
        parser.add_argument("--dry-run", action="store_true", help="Simulation sans écriture en base")
        parser.add_argument("--skip-existing", action="store_true",
                            help="Passer les leçons dont tous les exercices ont déjà un audio partagé")

    def handle(self, *args, **options):
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
                if len(audio_ids) == 1:
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
