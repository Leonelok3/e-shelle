"""
Commande Django : import de leçons allemandes depuis un fichier JSON (généré via ChatGPT).

Format JSON attendu (tableau de leçons) :
[
  {
    "level": "A1",
    "skill": "GRAMMATIK",
    "exam_type": "GOETHE",
    "title": "Das Verb 'sein' im Präsens",
    "intro": "Dans cette leçon, tu vas apprendre à conjuguer le verbe 'être' en allemand.",
    "content": "<h3>Das Verb sein</h3><p>...</p>",
    "exercises": [
      {
        "question_text": "Wie heißt 'ich bin' auf Deutsch?",
        "option_a": "ich bin",
        "option_b": "ich ist",
        "option_c": "ich sind",
        "option_d": "ich bist",
        "correct_option": "A",
        "explanation": "'Ich bin' est la forme correcte de 'sein' à la 1ère personne."
      }
    ]
  }
]

Usage :
    python manage.py import_german_lessons --file data/lessons_json/de_A1_goethe.json
    python manage.py import_german_lessons --file data/lessons_json/de_all.json --continue-on-error
    python manage.py import_german_lessons --file data/lessons_json/de_A1.json --flush --level A1
"""
import json
import logging

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from GermanPrepApp.models import GermanExam, GermanExercise, GermanLesson

logger = logging.getLogger(__name__)

VALID_SKILLS = {"GRAMMATIK", "WORTSCHATZ", "HOREN", "LESEN", "SPRECHEN", "SCHREIBEN"}
VALID_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
VALID_EXAM_TYPES = {"GOETHE", "TELC", "TESTDAF", "DSH", "GENERAL", "INTEGRATION"}
VALID_CORRECT = {"A", "B", "C", "D"}

EXAM_TYPE_LABELS = {
    "GOETHE": "Goethe-Zertifikat",
    "TELC": "telc Deutsch",
    "TESTDAF": "TestDaF",
    "DSH": "DSH",
    "GENERAL": "Général / Visa",
    "INTEGRATION": "Test d'intégration",
}


def _get_or_create_exam(level: str, exam_type: str) -> GermanExam:
    exam_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)
    title = f"{exam_label} {level}"
    slug = slugify(f"{exam_type}-{level}").lower()

    exam, _ = GermanExam.objects.get_or_create(
        slug=slug,
        defaults={
            "title": title,
            "short_description": (
                f"Préparation {exam_label} niveau {level} — leçons et exercices en allemand."
            ),
            "description": (
                f"Ce parcours couvre toutes les compétences nécessaires pour le "
                f"{exam_label} niveau {level} : Hören, Lesen, Sprechen, Schreiben, "
                f"Grammatik, Wortschatz."
            ),
            "exam_type": exam_type,
            "level": level,
            "is_active": True,
        },
    )
    return exam


def _validate_lesson(lesson_data: dict, idx: int) -> None:
    for field in ("level", "skill", "title", "content", "exercises"):
        if field not in lesson_data:
            raise ValueError(f"Leçon {idx}: champ manquant '{field}'")

    level = lesson_data["level"].upper()
    skill = lesson_data["skill"].upper()

    if level not in VALID_LEVELS:
        raise ValueError(f"Leçon {idx}: level='{level}' invalide. Valides: {VALID_LEVELS}")
    if skill not in VALID_SKILLS:
        raise ValueError(f"Leçon {idx}: skill='{skill}' invalide. Valides: {VALID_SKILLS}")

    exercises = lesson_data["exercises"]
    if not isinstance(exercises, list):
        raise ValueError(f"Leçon {idx}: 'exercises' doit être une liste.")

    for j, ex in enumerate(exercises):
        for f in ("question_text", "option_a", "option_b", "correct_option"):
            if f not in ex:
                raise ValueError(f"Leçon {idx} exercice {j}: champ manquant '{f}'")
        if ex["correct_option"].upper() not in VALID_CORRECT:
            raise ValueError(
                f"Leçon {idx} exercice {j}: correct_option='{ex['correct_option']}' invalide."
            )


class Command(BaseCommand):
    help = "Importe des leçons allemandes depuis un fichier JSON dans GermanPrepApp"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Chemin vers le fichier JSON (ex: data/lessons_json/de_A1_goethe.json)",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Supprimer les leçons existantes pour le niveau+exam_type avant import",
        )
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Filtrer uniquement ce niveau lors du flush (ex: A1)",
        )
        parser.add_argument(
            "--exam_type",
            type=str,
            default=None,
            help="Filtrer uniquement cet exam_type lors du flush (ex: GOETHE)",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continuer en cas d'erreur sur une leçon",
        )

    def handle(self, *args, **options):
        filepath = options["file"]
        flush = options["flush"]
        level_filter = options["level"].upper() if options["level"] else None
        exam_type_filter = options["exam_type"].upper() if options["exam_type"] else None
        continue_on_error = options["continue_on_error"]

        # Lecture du fichier JSON
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
            self.stderr.write("Le fichier JSON doit être un tableau de leçons.")
            return

        self.stdout.write(f"📂 {len(data)} leçon(s) trouvée(s) dans {filepath}")

        # Flush si demandé
        if flush:
            qs = GermanLesson.objects.all()
            if level_filter:
                qs = qs.filter(exam__level=level_filter)
            if exam_type_filter:
                qs = qs.filter(exam__exam_type=exam_type_filter)
            deleted_count = qs.count()
            qs.delete()
            self.stdout.write(
                self.style.WARNING(f"  {deleted_count} leçon(s) supprimée(s) avant import.")
            )

        created = 0
        skipped = 0

        for idx, lesson_data in enumerate(data):
            try:
                _validate_lesson(lesson_data, idx)

                level = lesson_data["level"].upper()
                skill = lesson_data["skill"].upper()
                exam_type = lesson_data.get("exam_type", "GOETHE").upper()

                exam = _get_or_create_exam(level, exam_type)

                # Ordre = nb leçons existantes + 1
                order = GermanLesson.objects.filter(exam=exam).count() + 1

                lesson = GermanLesson.objects.create(
                    exam=exam,
                    title=lesson_data["title"][:255],
                    skill=skill,
                    order=order,
                    intro=lesson_data.get("intro", "")[:500],
                    content=lesson_data.get("content", ""),
                )

                for ex_data in lesson_data["exercises"]:
                    GermanExercise.objects.create(
                        lesson=lesson,
                        question_text=ex_data["question_text"],
                        option_a=ex_data["option_a"][:255],
                        option_b=ex_data["option_b"][:255],
                        option_c=ex_data.get("option_c", "")[:255],
                        option_d=ex_data.get("option_d", "")[:255],
                        correct_option=ex_data["correct_option"].upper(),
                        explanation=ex_data.get("explanation", ""),
                    )

                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{idx+1}] ✅ {level}/{skill} — {lesson.title}"
                    )
                )

            except Exception as exc:
                skipped += 1
                msg = f"  [{idx+1}] ❌ ERREUR : {exc}"
                logger.warning("import_german_lessons: %s", exc)
                if continue_on_error:
                    self.stdout.write(self.style.WARNING(msg))
                else:
                    self.stderr.write(msg)
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Import terminé : {created} leçon(s) créée(s), {skipped} ignorée(s)."
            )
        )
