"""
Celery agents for the German preparation app.

They keep the German exam catalogue, lessons, exercises, placement questions,
and Horen audio populated without requiring manual admin actions.
"""
import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.utils.text import slugify

from .models import GermanExam, GermanLesson, GermanPastExam, GermanPlacementQuestion

log = logging.getLogger(__name__)


EXAM_TYPE_LABELS = {
    "GOETHE": "Goethe-Zertifikat",
    "TELC": "telc Deutsch",
    "TESTDAF": "TestDaF",
    "DSH": "DSH",
    "GENERAL": "General / Visa",
    "INTEGRATION": "Test d'integration",
}

GERMAN_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def _ensure_exam(level: str, exam_type: str = "GOETHE") -> tuple[GermanExam, bool]:
    exam_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)
    title = f"{exam_label} {level}"
    slug = slugify(f"{exam_type}-{level}").lower()
    return GermanExam.objects.get_or_create(
        slug=slug,
        defaults={
            "title": title,
            "short_description": (
                f"Preparation {exam_label} niveau {level} avec lecons, exercices "
                "cibles et simulations d'examen."
            ),
            "description": (
                f"Parcours complet pour preparer {exam_label} {level}: Horen, "
                "Lesen, Sprechen, Schreiben, Grammatik et Wortschatz."
            ),
            "exam_type": exam_type,
            "level": level,
            "is_active": True,
        },
    )


def _task_result(**values: Any) -> dict[str, Any]:
    return {"app": "GermanPrepApp", **values}


@shared_task(bind=True, max_retries=2, default_retry_delay=900)
def ensure_german_exam_catalog(self, exam_type: str = "GOETHE"):
    """
    Creates the visible Goethe A1-C2 catalogue even before AI content is ready.
    """
    created = 0
    existing = 0
    for level in GERMAN_LEVELS:
        _, was_created = _ensure_exam(level, exam_type.upper())
        if was_created:
            created += 1
        else:
            existing += 1

    log.info("ensure_german_exam_catalog: %s created, %s existing", created, existing)
    return _task_result(created=created, existing=existing, exam_type=exam_type.upper())


@shared_task(bind=True, max_retries=1, default_retry_delay=1800)
def generate_german_learning_content(self):
    """
    Tops up German courses and exercises in small daily batches.

    Defaults are intentionally conservative because every generated lesson may
    call an external LLM. Tune with:
    - GERMAN_AI_MIN_LESSONS_PER_LEVEL
    - GERMAN_AI_DAILY_LESSONS_PER_LEVEL
    - GERMAN_AI_EXERCISES_PER_LESSON
    """
    exam_type = getattr(settings, "GERMAN_AI_EXAM_TYPE", "GOETHE").upper()
    min_lessons = int(getattr(settings, "GERMAN_AI_MIN_LESSONS_PER_LEVEL", 25))
    daily_batch = int(getattr(settings, "GERMAN_AI_DAILY_LESSONS_PER_LEVEL", 2))
    exercises = int(getattr(settings, "GERMAN_AI_EXERCISES_PER_LESSON", 5))

    ensure_german_exam_catalog.run(exam_type=exam_type)

    generated_requests = []
    skipped = []

    for level in GERMAN_LEVELS:
        exam, _ = _ensure_exam(level, exam_type)
        current = GermanLesson.objects.filter(exam=exam).count()
        missing = max(0, min_lessons - current)
        if missing <= 0:
            skipped.append({"level": level, "current": current})
            continue

        lesson_count = min(daily_batch, missing)
        log.info(
            "generate_german_learning_content: generating %s lesson(s) for %s (%s/%s)",
            lesson_count,
            level,
            current,
            min_lessons,
        )
        call_command(
            "generate_german_content",
            level=level,
            exam_type=exam_type,
            lessons=lesson_count,
            exercises=exercises,
            sleep=0.5,
            continue_on_error=True,
        )
        generated_requests.append(
            {"level": level, "requested": lesson_count, "before": current}
        )

    return _task_result(
        exam_type=exam_type,
        min_lessons_per_level=min_lessons,
        generated_requests=generated_requests,
        skipped=skipped,
    )


@shared_task(bind=True, max_retries=1, default_retry_delay=1800)
def generate_german_placement_questions(self):
    """
    Keeps the German placement test usable.
    """
    target = int(getattr(settings, "GERMAN_AI_PLACEMENT_TARGET", 25))
    current = GermanPlacementQuestion.objects.filter(is_active=True).count()
    if current >= target:
        return _task_result(current=current, target=target, generated=0)

    to_generate = target - current
    call_command(
        "generate_german_placement",
        questions=to_generate,
        continue_on_error=True,
    )
    final_count = GermanPlacementQuestion.objects.filter(is_active=True).count()
    return _task_result(current=current, target=target, generated=final_count - current)


@shared_task(bind=True, max_retries=1, default_retry_delay=1800)
def generate_german_horen_audio(self):
    """
    Generates missing TTS audio for German Horen lessons.
    """
    call_command("generate_german_audio", continue_on_error=True)
    remaining = GermanLesson.objects.filter(skill="HOREN", audio_url="").count()
    return _task_result(remaining_horen_without_audio=remaining)


@shared_task(bind=True, max_retries=1, default_retry_delay=1800)
def generate_german_mock_exams(self):
    """
    Keeps downloadable German mock exams available for every Goethe level.
    """
    exam_type = getattr(settings, "GERMAN_AI_EXAM_TYPE", "GOETHE").upper()
    target = int(getattr(settings, "GERMAN_AI_MOCK_EXAMS_PER_LEVEL", 2))
    questions = int(getattr(settings, "GERMAN_AI_MOCK_EXAM_QUESTIONS", 40))

    ensure_german_exam_catalog.run(exam_type=exam_type)
    before = GermanPastExam.objects.filter(
        exam__exam_type=exam_type,
        title__startswith="Examen blanc IA",
        is_active=True,
    ).count()
    call_command(
        "generate_german_mock_exams",
        exam_type=exam_type,
        target=target,
        questions=questions,
        continue_on_error=True,
    )
    after = GermanPastExam.objects.filter(
        exam__exam_type=exam_type,
        title__startswith="Examen blanc IA",
        is_active=True,
    ).count()
    return _task_result(
        exam_type=exam_type,
        target_per_level=target,
        mock_exam_questions=questions,
        generated=after - before,
        total=after,
    )
