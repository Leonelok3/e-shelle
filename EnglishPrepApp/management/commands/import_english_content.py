"""
Import English tests + lessons + exercises from a JSON file.

Usage:
    python manage.py import_english_content data/lessons_json/en_A1.json
    python manage.py import_english_content data/lessons_json/en_A1.json --flush
"""
import json
from django.core.management.base import BaseCommand, CommandError
from EnglishPrepApp.models import (
    EnglishTest, EnglishQuestion, EnglishLesson, EnglishExercise
)

VALID_LEVELS     = {"A1", "A2", "B1", "B2", "C1", "C2"}
VALID_EXAM_TYPES = {"GENERAL", "IELTS", "TOEFL", "TOEIC"}
VALID_SKILLS     = {"READING", "LISTENING", "WRITING", "SPEAKING", "USE_OF_ENGLISH"}
VALID_OPTIONS    = {"A", "B", "C", "D"}
VALID_DIFFICULTY = {"EASY", "MEDIUM", "HARD"}


class Command(BaseCommand):
    help = "Import English tests, questions, lessons and exercises from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Path to JSON file.")
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete existing tests for the same level before importing."
        )
        parser.add_argument(
            "--continue-on-error", action="store_true",
            help="Skip errors and continue importing."
        )

    def handle(self, *args, **options):
        path = options["json_path"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Cannot read JSON: {e}")

        tests_data   = data.get("tests", [])
        lessons_data = data.get("lessons", [])

        if not tests_data:
            raise CommandError("JSON must contain a 'tests' key with at least one test.")

        # ── Optional flush ──
        if options["flush"]:
            levels = {t.get("level") for t in tests_data if t.get("level")}
            exam_types = {t.get("exam_type") for t in tests_data if t.get("exam_type")}
            deleted, _ = EnglishTest.objects.filter(
                level__in=levels, exam_type__in=exam_types
            ).delete()
            self.stdout.write(f"Flushed {deleted} existing tests.")

        test_map = {}   # name → EnglishTest instance
        t_created = t_updated = q_created = l_created = e_created = 0

        # ── Import tests + questions ──
        for td in tests_data:
            try:
                level     = td.get("level", "").upper()
                exam_type = td.get("exam_type", "GENERAL").upper()
                name      = td.get("name", "").strip()

                if level not in VALID_LEVELS:
                    raise ValueError(f"Invalid level: {level}")
                if exam_type not in VALID_EXAM_TYPES:
                    raise ValueError(f"Invalid exam_type: {exam_type}")
                if not name:
                    raise ValueError("'name' is required for each test.")

                test, created = EnglishTest.objects.update_or_create(
                    name=name,
                    defaults={
                        "exam_type":        exam_type,
                        "level":            level,
                        "duration_minutes": int(td.get("duration_minutes", 20)),
                        "description":      td.get("description", ""),
                        "is_active":        bool(td.get("is_active", True)),
                    }
                )
                test_map[name] = test
                if created:
                    t_created += 1
                else:
                    t_updated += 1

                # Questions
                for qd in td.get("questions", []):
                    skill   = qd.get("skill", "USE_OF_ENGLISH").upper()
                    correct = qd.get("correct_option", "A").upper()

                    if skill not in VALID_SKILLS:
                        skill = "USE_OF_ENGLISH"
                    if correct not in VALID_OPTIONS:
                        correct = "A"

                    EnglishQuestion.objects.create(
                        test=test,
                        skill=skill,
                        question_text=qd.get("question_text", qd.get("prompt", "")),
                        option_a=qd.get("option_a", ""),
                        option_b=qd.get("option_b", ""),
                        option_c=qd.get("option_c", ""),
                        option_d=qd.get("option_d", ""),
                        correct_option=correct,
                        explanation=qd.get("explanation", ""),
                        audio_url=qd.get("audio_url", ""),
                    )
                    q_created += 1

            except Exception as exc:
                if options["continue_on_error"]:
                    self.stderr.write(f"[SKIP test] {exc}")
                else:
                    raise CommandError(f"Error importing test '{td.get('name')}': {exc}")

        # ── Import lessons + exercises ──
        for ld in lessons_data:
            try:
                test_name = ld.get("test_name", "")
                test = test_map.get(test_name)
                if test is None:
                    # Try to find existing test by name
                    test = EnglishTest.objects.filter(name=test_name).first()
                if test is None:
                    raise ValueError(f"Unknown test_name: '{test_name}'")

                skill = ld.get("skill", "USE_OF_ENGLISH").upper()
                if skill not in VALID_SKILLS:
                    skill = "USE_OF_ENGLISH"

                level = ld.get("level", test.level).upper()
                if level not in VALID_LEVELS:
                    level = test.level

                lesson, _ = EnglishLesson.objects.update_or_create(
                    test=test,
                    title=ld.get("title", ""),
                    defaults={
                        "skill":             skill,
                        "goal":              ld.get("goal", ""),
                        "level":             level,
                        "short_description": ld.get("short_description", ""),
                        "content":           ld.get("content", ""),
                        "video_url":         ld.get("video_url", ""),
                        "order":             int(ld.get("order", 1)),
                    }
                )
                l_created += 1

                for ex in ld.get("exercises", []):
                    difficulty = ex.get("difficulty", "EASY").upper()
                    if difficulty not in VALID_DIFFICULTY:
                        difficulty = "EASY"
                    EnglishExercise.objects.create(
                        lesson=lesson,
                        title=ex.get("title", ""),
                        difficulty=difficulty,
                        description=ex.get("description", ""),
                        content=ex.get("content", ""),
                        external_url=ex.get("external_url", ""),
                        order=int(ex.get("order", 1)),
                    )
                    e_created += 1

            except Exception as exc:
                if options["continue_on_error"]:
                    self.stderr.write(f"[SKIP lesson] {exc}")
                else:
                    raise CommandError(f"Error importing lesson '{ld.get('title')}': {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"✓ Import terminé — Tests: +{t_created} créés / {t_updated} mis à jour | "
            f"Questions: +{q_created} | Leçons: +{l_created} | Exercices: +{e_created}"
        ))
