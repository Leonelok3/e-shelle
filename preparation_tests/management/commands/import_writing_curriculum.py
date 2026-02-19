"""
Management command: import_writing_curriculum
Importe le curriculum Expression Écrite (EE) depuis JSON
"""

import json
from django.core.management.base import BaseCommand
from django.db import transaction
from preparation_tests.models import CourseLesson, CourseExercise


class Command(BaseCommand):
    help = "Importe le curriculum EE (Expression Écrite) depuis JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Chemin vers le fichier JSON du curriculum EE",
        )
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Niveau (A1-C2) optionnel",
        )
        parser.add_argument(
            "--language",
            type=str,
            default="fr",
            help="Code langue (défaut: fr)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Supprime les leçons EE existantes avant import",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options["file"]
        language = options["language"]
        clear = options["clear"]

        # Charger le JSON
        self.stdout.write("[IMPORT] Loading JSON file...")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.stdout.write("[OK] JSON file loaded")
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"[ERROR] File not found: {file_path}"))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("[ERROR] Invalid JSON format"))
            return

        level = data.get("level", "").upper()
        section = data.get("section", "ee")
        lessons_data = data.get("lessons", [])

        # Supprimer les leçons EE si demandé
        if clear:
            self.stdout.write("[ACTION] Clearing existing EE lessons...")
            CourseLesson.objects.filter(section="ee").delete()
            self.stdout.write("[OK] EE lessons cleared")

        # Importer les leçons et exercices
        lessons_created = 0
        exercises_created = 0

        for lesson_data in lessons_data:
            lesson_num = lesson_data.get("lesson_number", 0)
            title = lesson_data.get("title", f"Lesson {lesson_num}")
            slug = lesson_data.get("slug", f"ee-{level.lower()}-lesson-{lesson_num}")
            objective = lesson_data.get("objective", title)
            vocabulary = lesson_data.get("vocabulary_focus", [])

            # Créer ou obtenir la leçon
            lesson, created = CourseLesson.objects.get_or_create(
                section=section,
                level_code=level,
                lesson_number=lesson_num,
                defaults={
                    "title": title,
                    "slug": slug,
                    "objective": objective,
                    "locale": language,
                    "content_html": f"<h2>{title}</h2><p>{objective}</p>",
                },
            )

            status = "[OK]" if created else "[EXISTS]"
            self.stdout.write(f"  {status} Lesson {lesson_num}: {title}")

            # Importer les exercices
            exercises_data = lesson_data.get("exercises", [])
            for exercise_data in exercises_data:
                ex = exercise_data.get("exercise", {})
                ex_num = ex.get("exercise_number", 0)

                exercise, _ = CourseExercise.objects.get_or_create(
                    lesson=lesson,
                    exercise_number=ex_num,
                    defaults={
                        "objective": ex.get("objective", f"Exercise {ex_num}"),
                        "prompt": ex.get("prompt", ""),
                        "word_count_min": ex.get("word_count_min", 50),
                        "word_count_max": ex.get("word_count_max", 150),
                        "context_info": ex.get("context", ""),
                        "example_answer": ex.get("example_answer", ""),
                        "evaluation_criteria": ex.get("evaluation_criteria", {}),
                        "difficulty_level": ex.get("difficulty_level", level),
                        "common_mistakes": ex.get("common_mistakes", ""),
                    },
                )
                exercises_created += 1

            self.stdout.write(
                f"    [IMPORT] {exercises_created} exercises for lesson {lesson_num}"
            )
            lessons_created += 1

        # Résumé
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("[SUMMARY] EE Curriculum Import")
        self.stdout.write("=" * 60)
        self.stdout.write(f"[STAT] Lessons created: {lessons_created}")
        self.stdout.write(f"[STAT] Exercises created: {exercises_created}")
        self.stdout.write(f"[STAT] Level: {level}")
        self.stdout.write(f"[STAT] Section: Expression Écrite (EE)")
        self.stdout.write(f"[STAT] Language: {language}")
        self.stdout.write("=" * 60)
        self.stdout.write("\n[SUCCESS] EE curriculum ready for students!")
