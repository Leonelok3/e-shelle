from unittest.mock import patch

from django.test import SimpleTestCase

from ai_engine.agents.ce_agent import generate_ce_content


class CEAgentTests(SimpleTestCase):
    @patch("ai_engine.agents.ce_agent.validate_ce_json")
    @patch("ai_engine.agents.ce_agent.call_llm")
    def test_generate_ce_content_success_first_try(self, call_llm_mock, validate_mock):
        call_llm_mock.return_value = """
        {
          "reading_text": "Texte CE",
          "questions": [
            {"question":"Q1","choices":["A","B"],"correct_answer":"A"}
          ]
        }
        """
        data = generate_ce_content("fr", "A1")
        self.assertIn("reading_text", data)
        self.assertIn("questions", data)
        validate_mock.assert_called_once()