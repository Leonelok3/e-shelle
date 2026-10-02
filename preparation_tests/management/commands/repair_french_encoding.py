"""Deterministic encoding repair with a mandatory pre-change JSON backup."""
import json
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from preparation_tests.models import CourseLesson
from preparation_tests.services.listening_material import repair_encoding, repair_seed_text, listening_script, seed_listening_explanation


class Command(BaseCommand):
    help = "Répare les caractères mal encodés, sans inventer les accents manquants. Simulation par défaut."

    def add_arguments(self, parser):
        parser.add_argument("--exam", choices=("tcf", "tef"), default="tcf")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        lessons = CourseLesson.objects.filter(locale__startswith="fr").filter(
            Q(exam__code__iexact=options["exam"]) | Q(exams__code__iexact=options["exam"])
        ).distinct().prefetch_related("exercises")
        changes = []
        objects = []
        for lesson in lessons:
            for instance, fields in [(lesson, ("title", "content_html"))] + [
                (ex, ("title", "instruction", "question_text", "document_title", "document_text",
                      "option_a", "option_b", "option_c", "option_d", "summary"))
                for ex in lesson.exercises.all()]:
                changed = {}
                for field in fields:
                    before = getattr(instance, field)
                    after = repair_encoding(before)
                    if lesson.slug.startswith("tcf-advanced-"):
                        after = repair_seed_text(after)
                    if after != before:
                        changed[field] = {"before": before, "after": after}
                if instance is not lesson and lesson.slug.startswith("tcf-advanced-") and lesson.section == "co":
                    generic = ["La situation est simple et ne présente aucune tension.",
                               "La décision depend d'une condition ou d'une nuance importante.",
                               "Le locuteur rejette totalement la proposition évoquée.",
                               "Le locuteur se limite à donner une information administrative."]
                    generic = [repair_seed_text(value) for value in generic]
                    current = [repair_seed_text(getattr(instance, "option_" + letter)) for letter in "abcd"]
                    from preparation_tests.management.commands.seed_tcf_advanced_content import Command as SeedCommand
                    known_scripts = {
                        repair_seed_text(SeedCommand()._co_data(lesson.level, "", order)["instruction"].split(":", 1)[1].strip())
                        for order in range(1, 6)
                    }
                    script = repair_seed_text(listening_script(instance))
                    if current == generic and script in known_scripts:
                        legacy_summary = "La bonne réponse tient compte de la concession et de la condition exprimées dans le script."
                        if repair_seed_text(instance.summary) == legacy_summary:
                            changed["summary"] = {"before": instance.summary, "after": seed_listening_explanation(script)}
                        if instance.correct_option != "B":
                            changed["correct_option"] = {"before": instance.correct_option, "after": "B"}
                    if not instance.document_text and listening_script(instance):
                        changed["document_text"] = {"before": "", "after": repair_seed_text(listening_script(instance))}
                if changed:
                    changes.append({"model": instance._meta.label, "id": instance.pk, "fields": changed})
                    objects.append((instance, changed))
        self.stdout.write(f"{len(changes)} objets à corriger ; apply={options['apply']}")
        if not options["apply"] or not changes:
            return
        folder = Path(settings.BASE_DIR) / "output" / "tcf_tef_quality"
        folder.mkdir(parents=True, exist_ok=True)
        backup = folder / ("encoding_backup_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        # Write complete rollback values before any database change.
        with backup.open("x", encoding="utf-8") as stream:
            json.dump(changes, stream, ensure_ascii=False, indent=2)
        with transaction.atomic():
            for instance, changed in objects:
                # Conditional update avoids overwriting concurrent editorial changes.
                filters = {key: item["before"] for key, item in changed.items()}
                updates = {key: item["after"] for key, item in changed.items()}
                updated = type(instance).objects.filter(pk=instance.pk, **filters).update(**updates)
                if updated != 1:
                    raise CommandError("Contenu modifié pendant la réparation ; opération annulée.")
        self.stdout.write(f"Correction terminée. Sauvegarde : {backup}")
