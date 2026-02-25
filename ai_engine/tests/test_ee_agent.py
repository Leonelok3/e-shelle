from unittest.mock import patch

from django.test import SimpleTestCase

from ai_engine.agents.ee_agent import generate_ee_content


class EEAgentTests(SimpleTestCase):
    @patch("ai_engine.agents.ee_agent.validate_ee_json")
    @patch("ai_engine.agents.ee_agent.call_llm")
    def test_generate_ee_content_success_first_try(self, call_llm_mock, validate_mock):
        call_llm_mock.return_value = """
        {
          "topic": "Mon projet professionnel",
          "instructions": "Rédigez un texte structuré.",
          "min_words": 120,
          "sample_answer": "Je souhaite travailler dans..."
        }
        """
        data = generate_ee_content("fr", "B1")
        self.assertIn("topic", data)
        self.assertIn("instructions", data)
        self.assertIn("min_words", data)
        self.assertIn("sample_answer", data)
        validate_mock.assert_called_once()