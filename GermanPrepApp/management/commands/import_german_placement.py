"""
Commande Django : import des questions du placement test allemand depuis JSON.

Format JSON attendu :
[
  {
    "question_text": "Was ist die richtige Form von 'sein' für 'ich'?",
    "option_a": "ich bin",
    "option_b": "ich ist",
    "option_c": "ich sind",
    "option_d": "ich bist",
    "correct_option": "A",
    "level_hint": "A1"
  }
]

Usage :
    python manage.py import_german_placement --file data/lessons_json/de_placement.json
    python manage.py import_german_placement --file data/lessons_json/de_placement.json --replace
"""
import json
import logging

from django.core.management.base import BaseCommand

from GermanPrepApp.models import GermanPlacementQuestion

logger = logging.getLogger(__name__)

VALID_CORRECT = {"A", "B", "C", "D"}


class Command(BaseCommand):
    help = "Importe les questions du placement test allemand depuis un fichier JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Chemin vers le fichier JSON",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Supprimer toutes les questions existantes avant import",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continuer en cas d'erreur sur une question",
        )

    def handle(self, *args, **options):
        filepath = options["file"]
        replace = options["replace"]
        continue_on_error = options["continue_on_error"]

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f"Fichier introuvable : {filepath}")
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f"JSON invalide : {e}")
            return

        if not isinstance(data, list):
            self.stderr.write("Le fichier JSON doit être un tableau de questions.")
            return

        if replace:
            deleted, _ = GermanPlacementQuestion.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"  {deleted} question(s) supprimée(s)."))

        existing = GermanPlacementQuestion.objects.count()
        self.stdout.write(f"📂 {len(data)} question(s) à importer.")

        created = 0
        skipped = 0

        for idx, q in enumerate(data):
            try:
                for field in ("question_text", "option_a", "option_b", "correct_option"):
                    if field not in q:
                        raise ValueError(f"Champ manquant : '{field}'")
                if q["correct_option"].upper() not in VALID_CORRECT:
                    raise ValueError(f"correct_option='{q['correct_option']}' invalide.")

                GermanPlacementQuestion.objects.create(
                    question_text=q["question_text"],
                    option_a=q["option_a"][:255],
                    option_b=q["option_b"][:255],
                    option_c=q.get("option_c", "")[:255],
                    option_d=q.get("option_d", "")[:255],
                    correct_option=q["correct_option"].upper(),
                    order=existing + idx + 1,
                    is_active=True,
                )
                created += 1

            except Exception as exc:
                skipped += 1
                msg = f"  [{idx+1}] ❌ ERREUR : {exc}"
                if continue_on_error:
                    self.stdout.write(self.style.WARNING(msg))
                else:
                    self.stderr.write(msg)
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {created} question(s) créée(s), {skipped} ignorée(s). "
                f"Total : {existing + created} questions."
            )
        )
