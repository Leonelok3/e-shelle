#!/usr/bin/env python
"""
Script de validation rapide pour Expression Écrite (EE)
Vérifie que les données EE sont correctement importées en base de données
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from preparation_tests.models import CourseLesson, CourseExercise
from exam.models import Exam, Question, Choice


def validate_ee():
    """Valide les statistiques EE dans la base de données"""
    print("\n" + "=" * 60)
    print("[VALIDATION] Quick EE Check - All Systems Go!")
    print("=" * 60 + "\n")

    # Curriculum EE
    lessons = CourseLesson.objects.filter(section="ee")
    exercises = CourseExercise.objects.filter(lesson__section="ee")

    lessons_count = lessons.count()
    exercises_count = exercises.count()

    print(f"[CURRICULUM] EE: {lessons_count} lessons, {exercises_count} exercises")

    # Exams EE
    exams = Exam.objects.filter(code__startswith="EE_")
    questions = Question.objects.filter(
        exam_section__exam__code__startswith="EE_"
    )
    choices = Choice.objects.filter(question__exam_section__exam__code__startswith="EE_")

    exams_count = exams.count()
    questions_count = questions.count()
    choices_count = choices.count()

    print(f"[EXAMS] EE: {exams_count} exams, {questions_count} questions, {choices_count} choices")

    # Total
    total = lessons_count + exercises_count + exams_count + questions_count + choices_count
    print(f"\n[TOTAL] {total} items EE en base de donnees")

    # Vérification
    expected_lessons = 90  # 15 par niveau x 6 niveaux
    expected_exercises = 900  # 150 par niveau x 6 niveaux
    expected_exams = 6
    expected_questions = 195
    expected_choices = 780

    print("\n" + "-" * 60)

    success = True
    if lessons_count != expected_lessons:
        print(f"[WARNING] Expected {expected_lessons} lessons, got {lessons_count}")
        success = False
    else:
        print(f"[OK] Lessons: {lessons_count}/{expected_lessons}")

    if exercises_count != expected_exercises:
        print(f"[WARNING] Expected {expected_exercises} exercises, got {exercises_count}")
        success = False
    else:
        print(f"[OK] Exercises: {exercises_count}/{expected_exercises}")

    if exams_count != expected_exams:
        print(f"[WARNING] Expected {expected_exams} exams, got {exams_count}")
        success = False
    else:
        print(f"[OK] Exams: {exams_count}/{expected_exams}")

    if questions_count != expected_questions:
        print(f"[WARNING] Expected {expected_questions} questions, got {questions_count}")
        success = False
    else:
        print(f"[OK] Questions: {questions_count}/{expected_questions}")

    if choices_count != expected_choices:
        print(f"[WARNING] Expected {expected_choices} choices, got {choices_count}")
        success = False
    else:
        print(f"[OK] Choices: {choices_count}/{expected_choices}")

    print("-" * 60)

    if success:
        print("\n[SUCCESS] All EE validations passed!")
    else:
        print("\n[WARNING] Some counts don't match expected values")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    validate_ee()
