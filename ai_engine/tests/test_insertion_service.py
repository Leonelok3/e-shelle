from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from ai_engine.services.insertion_service import insert_co_content


class InsertCOContentTests(SimpleTestCase):
    @patch("ai_engine.services.insertion_service.transaction.atomic", return_value=nullcontext())
    def test_invalid_json_string_raises_explicit_error(self, _atomic):
        bad_json = '{"audio_script":"Bonjour", "questions":[}'  # JSON invalide

        with self.assertRaises(ValueError) as ctx:
            insert_co_content(
                exam_id=1,
                level="A1",
                language="fr",
                co_data=bad_json,
                audio_path="audio/test.mp3",
            )

        self.assertIn("Invalid JSON for co_data", str(ctx.exception))

    @patch("ai_engine.services.insertion_service.transaction.atomic", return_value=nullcontext())
    @patch("ai_engine.services.insertion_service.CourseExercise")
    @patch("ai_engine.services.insertion_service.CourseLesson")
    @patch("ai_engine.services.insertion_service.Asset")
    @patch("ai_engine.services.insertion_service.Exam")
    def test_valid_json_string_creates_lesson_and_exercises(
        self, ExamMock, AssetMock, CourseLessonMock, CourseExerciseMock, _atomic
    ):
        ExamMock.objects.get.return_value = SimpleNamespace(id=1)
        AssetMock.objects.create.return_value = SimpleNamespace(id=10)
        lesson_obj = SimpleNamespace(id=20)
        CourseLessonMock.objects.create.return_value = lesson_obj
        CourseExerciseMock.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
        CourseExerciseMock.objects = MagicMock()

        good_json = """
        {
          "audio_script": "Texte audio",
          "questions": [
            {"question": "Q1", "choices": ["A", "B"], "correct_answer": "A"},
            {"question": "Q2", "choices": ["C", "D"], "correct_answer": "D"}
          ]
        }
        """

        result = insert_co_content(
            exam_id=1,
            level="a1",
            language="FR",
            co_data=good_json,
            audio_path="audio/test.mp3",
        )

        self.assertEqual(result, lesson_obj)
        ExamMock.objects.get.assert_called_once_with(id=1)
        AssetMock.objects.create.assert_called_once()
        CourseLessonMock.objects.create.assert_called_once()
        CourseExerciseMock.objects.bulk_create.assert_called_once()