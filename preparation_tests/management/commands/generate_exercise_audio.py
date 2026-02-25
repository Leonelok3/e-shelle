from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from ai_engine.services.tts_service import generate_audio
from preparation_tests.models import Asset, CourseExercise


def _build_asset(rel_audio_path: str, language: str, title: str = "") -> Asset:
    """
    Création Asset robuste selon les champs réellement présents.
    """
    field_names = {f.name for f in Asset._meta.concrete_fields}
    kwargs = {}

    if "type" in field_names:
        kwargs["type"] = "audio"
    if "locale" in field_names:
        kwargs["locale"] = language
    if "title" in field_names and title:
        kwargs["title"] = title

    asset = Asset.objects.create(**kwargs)

    # Affectation du chemin fichier selon le modèle
    if "file" in field_names:
        setattr(asset, "file", rel_audio_path)
        asset.save(update_fields=["file"])
    elif "path" in field_names:
        setattr(asset, "path", rel_audio_path)
        asset.save(update_fields=["path"])
    else:
        # Pas de champ fichier connu
        asset.save()

    return asset


class Command(BaseCommand):
    help = "Génère audio pour les exercices CO et lie chaque audio à CourseExercise.audio"

    def add_arguments(self, parser):
        parser.add_argument("--language", type=str, default="fr")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--all", action="store_true", help="Traiter tous les exercices, même ceux ayant déjà un audio")

    def handle(self, *args, **options):
        language = (options["language"] or "fr").strip().lower()
        limit = int(options["limit"] or 0)
        process_all = bool(options["all"])

        qs = CourseExercise.objects.select_related("lesson", "audio").all()
        if not process_all:
            qs = qs.filter(Q(audio__isnull=True))

        if limit > 0:
            qs = qs[:limit]

        total = 0
        ok = 0
        skipped = 0
        failed = 0

        for ex in qs:
            total += 1
            try:
                source_text = (getattr(ex, "instruction", None) or "").strip()
                if not source_text:
                    source_text = (getattr(ex, "question_text", None) or "").strip()

                if not source_text:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"[skip] ex#{ex.id}: empty text"))
                    continue

                rel_audio = generate_audio(source_text, language=language)

                title = f"Exercice {ex.id} audio"
                asset = _build_asset(rel_audio, language=language, title=title)

                ex.audio = asset
                ex.save(update_fields=["audio"])

                ok += 1
                self.stdout.write(self.style.SUCCESS(f"[ok] ex#{ex.id} -> {rel_audio}"))

            except Exception as e:
                failed += 1
                self.stderr.write(self.style.ERROR(f"[fail] ex#{ex.id}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"Done total={total} ok={ok} skipped={skipped} failed={failed}")
        )