from django.db import transaction
from preparation_tests.models import CourseLesson, CourseExercise, Asset, Exam

def insert_co_content(exam_id, level, language, co_data, audio_path):
    with transaction.atomic():
        exam = Exam.objects.get(id=exam_id)

        asset = Asset.objects.create(
            file=audio_path,
            asset_type="audio"
        )

        lesson = CourseLesson.objects.create(
            exam=exam,
            section="co",
            level=level,
            content_html=co_data["audio_script"],
            locale=language
        )

        for q in co_data["questions"]:
            CourseExercise.objects.create(
                lesson=lesson,
                question=q["question"],
                choices=q["choices"],
                correct_answer=q["correct_answer"],
                audio=asset
            )
