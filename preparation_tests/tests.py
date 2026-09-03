import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import CourseExercise, CourseLesson, EESubmission, EOSubmission, Exam, ExamSection


class FrenchTcfAgentsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="tcf_staff",
            email="tcf_staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_login(self.user)

        self.exam = Exam.objects.create(code="tcf", name="TCF Canada", language="fr")
        for order, code in enumerate(["co", "ce", "ee", "eo"], start=1):
            ExamSection.objects.create(exam=self.exam, code=code, order=order, duration_sec=600)

        self.ee_lesson = self._lesson("ee")
        self.eo_lesson = self._lesson("eo")
        self.co_lesson = self._lesson("co")
        self.ce_lesson = self._lesson("ce")

        self.ee_exercise = self._exercise(self.ee_lesson, "Sujet EE")
        self.eo_exercise = self._exercise(self.eo_lesson, "Sujet EO")
        self._exercise(self.co_lesson, "Question CO")
        self._exercise(self.ce_lesson, "Question CE")

    def _lesson(self, section):
        lesson = CourseLesson.objects.create(
            exam=self.exam,
            section=section,
            level="B2",
            title=f"TCF B2 {section.upper()}",
            slug=f"test-tcf-b2-{section}",
            locale="fr",
            content_html="<p>Leçon de test.</p>",
            order=1,
            is_published=True,
        )
        lesson.exams.add(self.exam)
        return lesson

    def _exercise(self, lesson, question):
        return CourseExercise.objects.create(
            lesson=lesson,
            title=f"Exercice {lesson.section.upper()}",
            instruction="Consigne de test.",
            question_text=question,
            option_a="Option A",
            option_b="Option B",
            option_c="Option C",
            option_d="Option D",
            correct_option="A",
            summary="Explication de test.",
            order=1,
            is_active=True,
        )

    @patch("ai_engine.services.llm_service.call_llm", return_value="Plan B2: CO, CE, EE, EO.")
    def test_french_ai_coach_api_returns_reply(self, call_llm):
        response = self.client.post(
            reverse("preparation_tests:ai_coach_api"),
            data=json.dumps({"message": "Donne-moi un plan TCF B2.", "history": []}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Plan B2: CO, CE, EE, EO.")
        call_llm.assert_called_once()

    @patch(
        "ai_engine.services.eval_service.evaluate_ee",
        return_value={
            "score": 82,
            "feedback": "Production claire.",
            "errors": [],
            "corrected_version": "Version améliorée.",
            "criteria": {"coherence": 80},
        },
    )
    def test_submit_ee_saves_ai_feedback(self, evaluate_ee):
        response = self.client.post(
            reverse("preparation_tests:submit_ee"),
            data=json.dumps({"exercise_id": self.ee_exercise.id, "text": "Voici ma réponse argumentée."}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(EESubmission.objects.count(), 1)
        self.assertEqual(EESubmission.objects.first().score, 82)
        evaluate_ee.assert_called_once()

    @patch("ai_engine.services.eval_service.transcribe_audio", return_value="Je donne mon avis avec deux arguments.")
    @patch(
        "ai_engine.services.eval_service.evaluate_eo",
        return_value={
            "score": 78,
            "feedback": "Oral structuré.",
            "points_covered": ["position claire"],
            "suggestions": ["Ajouter un exemple."],
            "criteria": {"fluency": 75},
        },
    )
    def test_submit_eo_transcribes_and_saves_feedback(self, evaluate_eo, transcribe_audio):
        audio = SimpleUploadedFile("oral.webm", b"fake audio bytes", content_type="audio/webm")
        response = self.client.post(
            reverse("preparation_tests:submit_eo"),
            data={"exercise_id": self.eo_exercise.id, "audio": audio},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(EOSubmission.objects.count(), 1)
        self.assertEqual(EOSubmission.objects.first().score, 78)
        transcribe_audio.assert_called_once()
        evaluate_eo.assert_called_once()

    def test_tcf_course_section_and_official_mock_render(self):
        course_response = self.client.get(reverse("preparation_tests:course_section", args=["tcf", "ce"]))
        mock_response = self.client.get(reverse("preparation_tests:exam_format_exam", args=["tcf", "B2"]))

        self.assertEqual(course_response.status_code, 200)
        self.assertContains(course_response, "TCF B2 CE")
        self.assertEqual(mock_response.status_code, 200)
        self.assertContains(mock_response, "TCF")
