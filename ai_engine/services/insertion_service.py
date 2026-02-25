import json
from json import JSONDecodeError

from django.db import transaction
from preparation_tests.models import CourseLesson, CourseExercise, Asset, Exam


def insert_co_content(exam_id, level, language, co_data, audio_path):
    if not exam_id:
        raise ValueError("exam_id is required.")
    if not audio_path:
        raise ValueError("audio_path is required.")

    # Accepte dict OU string JSON
    if isinstance(co_data, str):
        try:
            co_data = json.loads(co_data)
        except JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for co_data: {e.msg}") from e

    if not isinstance(co_data, dict):
        raise ValueError("co_data must be a dict or a valid JSON string.")

    audio_script = (co_data.get("audio_script") or "").strip()
    questions = co_data.get("questions")

    if not audio_script:
        raise ValueError("co_data.audio_script is required.")
    if not isinstance(questions, list) or not questions:
        raise ValueError("co_data.questions must be a non-empty list.")

    lang = (language or "").strip().lower()
    lvl = (level or "").strip().upper()

    with transaction.atomic():
        exam = Exam.objects.get(id=exam_id)

        asset = Asset.objects.create(
            file=audio_path,
            asset_type="audio",
        )

        lesson = CourseLesson.objects.create(
            exam=exam,
            section="co",
            level=lvl,
            content_html=audio_script,
            locale=lang,
        )

        exercises = []
        for i, q in enumerate(questions, start=1):
            if not isinstance(q, dict):
                raise ValueError(f"Question #{i}: must be an object.")

            question = (q.get("question") or "").strip()
            choices = q.get("choices")
            correct_answer = q.get("correct_answer")

            if not question:
                raise ValueError(f"Question #{i}: 'question' is required.")
            if not isinstance(choices, list) or len(choices) < 2:
                raise ValueError(f"Question #{i}: 'choices' must contain at least 2 options.")
            if correct_answer is None:
                raise ValueError(f"Question #{i}: 'correct_answer' is required.")

            exercises.append(
                CourseExercise(
                    lesson=lesson,
                    question=question,
                    choices=choices,
                    correct_answer=correct_answer,
                    audio=asset,
                )
            )

        CourseExercise.objects.bulk_create(exercises)
        return lesson