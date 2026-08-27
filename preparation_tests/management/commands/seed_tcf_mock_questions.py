from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from preparation_tests.models import Choice, CourseExercise, Exam, ExamSection, Question


class Command(BaseCommand):
    help = "Create legacy mock-exam Question/Choice rows from TCF CourseExercise rows without duplicates."

    def add_arguments(self, parser):
        parser.add_argument("--levels", default="B2,C1,C2")
        parser.add_argument("--sections", default="co,ce,ee,eo")
        parser.add_argument("--limit-per-section-level", type=int, default=120)

    @transaction.atomic
    def handle(self, *args, **options):
        levels = [lv.strip().upper() for lv in options["levels"].split(",") if lv.strip()]
        sections = [s.strip().lower() for s in options["sections"].split(",") if s.strip()]
        limit = max(1, int(options["limit_per_section_level"]))

        exam = self._ensure_tcf_exam()

        created_questions = 0
        updated_questions = 0
        created_choices = 0
        updated_choices = 0

        for section_code in sections:
            section = ExamSection.objects.get(exam=exam, code=section_code)
            for level in levels:
                exercises = (
                    CourseExercise.objects.filter(
                        lesson__exams=exam,
                        lesson__section=section_code,
                        lesson__level=level,
                        lesson__is_published=True,
                        is_active=True,
                    )
                    .select_related("lesson", "audio")
                    .order_by("lesson__order", "order")
                    .distinct()[:limit]
                )

                for exercise in exercises:
                    stem = self._stem_for_exercise(exercise, level, section_code)
                    question, q_created = Question.objects.update_or_create(
                        section=section,
                        stem=stem,
                        defaults={
                            "asset": exercise.audio if section_code == "co" else None,
                            "subtype": "mcq",
                            "difficulty": self._difficulty(level),
                        },
                    )
                    created_questions += int(q_created)
                    updated_questions += int(not q_created)

                    for text, is_correct in self._choices_for_exercise(exercise):
                        choice, c_created = Choice.objects.update_or_create(
                            question=question,
                            text=text,
                            defaults={"is_correct": is_correct},
                        )
                        created_choices += int(c_created)
                        updated_choices += int(not c_created)

        self.stdout.write(
            self.style.SUCCESS(
                "TCF mock questions OK: "
                f"{created_questions} questions creees, {updated_questions} mises a jour, "
                f"{created_choices} choix crees, {updated_choices} choix mis a jour."
            )
        )

    def _ensure_tcf_exam(self) -> Exam:
        exam, _ = Exam.objects.update_or_create(
            code="tcf",
            defaults={
                "name": "TCF Canada",
                "language": "fr",
                "description": "Preparation TCF Canada: CO, CE, EE, EO et examens blancs.",
            },
        )
        durations = {"co": 1500, "ce": 2700, "ee": 3600, "eo": 720}
        for order, code in enumerate(["co", "ce", "ee", "eo"], start=1):
            ExamSection.objects.update_or_create(
                exam=exam,
                code=code,
                defaults={"order": order, "duration_sec": durations[code]},
            )
        return exam

    def _stem_for_exercise(self, exercise: CourseExercise, level: str, section_code: str) -> str:
        prefix = f"[{level}][{section_code.upper()}]"
        if exercise.instruction:
            return f"{prefix} {exercise.instruction}\n\n{exercise.question_text}".strip()
        return f"{prefix} {exercise.question_text}".strip()

    def _choices_for_exercise(self, exercise: CourseExercise):
        correct = (exercise.correct_option or "").upper()
        options = [
            ("A", exercise.option_a),
            ("B", exercise.option_b),
            ("C", exercise.option_c),
            ("D", exercise.option_d),
        ]
        usable = [(letter, text) for letter, text in options if text]
        if len(usable) < 2:
            usable = [
                ("A", "Réponse complète et pertinente"),
                ("B", "Réponse partielle ou hors sujet"),
            ]
            correct = "A"
        for letter, text in usable:
            yield text, letter == correct

    def _difficulty(self, level: str) -> str:
        if level in {"C1", "C2"}:
            return "hard"
        if level in {"B1", "B2"}:
            return "medium"
        return "easy"
