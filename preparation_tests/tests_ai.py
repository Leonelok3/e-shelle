from unittest.mock import patch

from django.test import SimpleTestCase

from ai_engine.services.eval_service import evaluate_ee, evaluate_eo
from ai_engine.services.llm_service import call_llm


class AIAgentServiceTests(SimpleTestCase):
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
