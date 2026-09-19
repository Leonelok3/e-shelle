import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from ai_engine.services.eval_service import evaluate_ee, evaluate_eo, transcribe_audio
from ai_engine.services.llm_service import call_llm


@override_settings(OPENAI_API_KEY="test-only", AI_CONTENT_MODE="auto")
class AIAgentServiceTests(SimpleTestCase):
    def setUp(self):
        from ai_engine.services.availability import reset
        reset()
        for name in ("_call_gemini_eval_json", "_call_anthropic_eval_json"):
            provider = patch("ai_engine.services.eval_service." + name,
                             side_effect=RuntimeError("provider unavailable"))
            provider.start()
            self.addCleanup(provider.stop)

    @patch("ai_engine.services.eval_service.call_openai_json", side_effect=RuntimeError("quota"))
    def test_french_grading_does_not_invent_a_score_when_providers_fail(self, provider):
        with self.assertRaises(RuntimeError):
            evaluate_ee("Texte test", "Sujet", "Consigne", "B2", "fr", require_ai=True)
        with self.assertRaises(RuntimeError):
            evaluate_eo("Texte test", "Sujet", "Consigne", "B2", [], "fr", require_ai=True)

    @override_settings(OPENAI_API_KEY="")
    @patch("ai_engine.services.eval_service.get_vertex_client", return_value=(None, "unavailable"))
    @patch("ai_engine.services.eval_service.get_genai_studio_client", return_value=(None, "unavailable"))
    def test_transcription_failure_does_not_return_invented_speech(self, studio, vertex):
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder) / "test.webm"
            audio.write_bytes(b"test")
            self.assertEqual(transcribe_audio(str(audio), language="fr"), "")

    @override_settings(OPENAI_API_KEY="")
    @patch("ai_engine.services.eval_service.get_vertex_client", return_value=(None, "unavailable"))
    @patch("ai_engine.services.eval_service.get_genai_studio_client")
    def test_wav_transcription_uses_correct_mime_type(self, studio, vertex):
        client = Mock()
        client.models.generate_content.return_value.text = "Bonjour."
        studio.return_value = (client, None)
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder) / "test.wav"
            audio.write_bytes(b"test")
            self.assertEqual(transcribe_audio(str(audio), language="fr"), "Bonjour.")
        part = client.models.generate_content.call_args.kwargs["contents"][0]
        self.assertEqual(part.inline_data.mime_type, "audio/wav")

    @patch("ai_engine.services.openai_adapter.call_openai", return_value="Leçon générée.")
    def test_llm_service_uses_openai_adapter(self, call_openai):
        result = call_llm("Tu es coach TCF.", "Génère une mini leçon CO B2.")

        self.assertEqual(result, "Leçon générée.")
        call_openai.assert_called_once()

    @patch(
        "ai_engine.services.eval_service.call_openai_json",
        return_value={
            "score": 80,
            "feedback": "Texte clair.",
            "corrected_version": "Version corrigée.",
            "errors": [],
            "criteria": {"grammar": 80},
        },
    )
    def test_evaluate_ee_returns_structured_feedback(self, call_openai_json):
        result = evaluate_ee(
            text="Je pense que cette idée est utile.",
            topic="Donnez votre opinion.",
            instructions="Répondez de façon argumentée.",
            level="B2",
            language="fr",
        )

        self.assertEqual(result["score"], 80)
        self.assertIn("feedback", result)
        call_openai_json.assert_called_once()

    @patch(
        "ai_engine.services.eval_service.call_openai_json",
        return_value={
            "score": 78,
            "feedback": "Oral structuré.",
            "points_covered": ["position claire"],
            "suggestions": ["Ajouter un exemple."],
            "criteria": {"pronunciation": 75},
        },
    )
    def test_evaluate_eo_returns_structured_feedback(self, call_openai_json):
        result = evaluate_eo(
            transcript="Je suis favorable à cette mesure pour deux raisons.",
            topic="Présentez votre opinion.",
            instructions="Parlez deux minutes.",
            level="B2",
            expected_points=["position claire"],
            language="fr",
        )

        self.assertEqual(result["score"], 78)
        self.assertIn("suggestions", result)
        call_openai_json.assert_called_once()
