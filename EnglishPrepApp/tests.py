import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from . import views
from .models import EnglishEESubmission, EnglishEOSubmission, EnglishLesson, EnglishQuestion, EnglishTest


def _fake_openai_reply(text):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text)
            )
        ]
    )


class _FakeChatCompletions:
    def create(self, **kwargs):
        return _fake_openai_reply("Plan IA anglais OK")


class _FakeOpenAIClient:
    chat = SimpleNamespace(completions=_FakeChatCompletions())


@override_settings(OPENAI_API_KEY="test-key")
class EnglishPrepAgentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="agent_user",
            email="agent@example.com",
            password="pass12345",
        )
        self.test = EnglishTest.objects.create(
            name="IELTS Canada B2",
            exam_type="IELTS",
            level="B2",
            duration_minutes=20,
            is_active=True,
        )
        self.reading_question = EnglishQuestion.objects.create(
            test=self.test,
            skill="READING",
            question_text="Read the notice. What is required?",
            option_a="A passport",
            option_b="A bike",
            correct_option="A",
        )
        self.listening_question = EnglishQuestion.objects.create(
            test=self.test,
            skill="LISTENING",
            question_text="Listen and choose the destination.",
            option_a="Toronto",
            option_b="Calgary",
            correct_option="B",
            audio_url="https://cdn.example.test/audio/listening-b2.mp3",
        )
        self.writing_lesson = EnglishLesson.objects.create(
            test=self.test,
            title="IELTS Writing Task 2",
            skill="WRITING",
            goal="Immigration Canada",
            level="B2",
            short_description="Write an opinion essay.",
        )
        self.speaking_lesson = EnglishLesson.objects.create(
            test=self.test,
            title="IELTS Speaking Part 2",
            skill="SPEAKING",
            goal="Immigration Canada",
            level="B2",
            short_description="Speak about a professional goal.",
        )

    def test_listening_test_page_renders_audio_prompt(self):
        response = self.client.get(reverse("englishprep:take_test", args=[self.test.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://cdn.example.test/audio/listening-b2.mp3")
        self.assertContains(response, "Listening")

    def test_ai_coach_page_post_returns_answer(self):
        self.client.force_login(self.user)
        original_client = views.client
        views.client = _FakeOpenAIClient()
        try:
            response = self.client.post(
                reverse("englishprep:ai_coach"),
                {"question": "Comment progresser en IELTS listening ?"},
            )
        finally:
            views.client = original_client

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plan IA anglais OK")

    @patch("ai_engine.services.eval_service.evaluate_ee")
    def test_english_writing_submission_is_evaluated_and_saved(self, evaluate_ee):
        evaluate_ee.return_value = {
            "score": 82,
            "feedback": "Bonne structure.",
            "errors": [],
            "corrected_version": "Corrected text.",
            "criteria": {"grammar": 80},
        }
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("englishprep:submit_ee"),
            data=json.dumps({
                "exercise_id": self.writing_lesson.id,
                "text": "I think Canada is a good place to study because it is diverse.",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["score"], 82)
        self.assertEqual(EnglishEESubmission.objects.count(), 1)

    @patch("ai_engine.services.eval_service.evaluate_eo")
    @patch("ai_engine.services.eval_service.transcribe_audio")
    def test_english_speaking_submission_is_transcribed_evaluated_and_saved(self, transcribe_audio, evaluate_eo):
        transcribe_audio.return_value = "I want to work in Canada because I can grow professionally."
        evaluate_eo.return_value = {
            "score": 76,
            "feedback": "Réponse claire.",
            "points_covered": ["objectif professionnel"],
            "suggestions": ["Ajoute un exemple précis."],
            "criteria": {"pronunciation": 75},
        }
        self.client.force_login(self.user)
        audio = SimpleUploadedFile(
            "recording.webm",
            b"fake-audio-content",
            content_type="audio/webm",
        )

        response = self.client.post(
            reverse("englishprep:submit_eo"),
            data={"exercise_id": str(self.speaking_lesson.id), "audio": audio},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["score"], 76)
        self.assertEqual(payload["transcript"], transcribe_audio.return_value)
        self.assertEqual(EnglishEOSubmission.objects.count(), 1)
