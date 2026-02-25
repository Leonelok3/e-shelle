from django.test import SimpleTestCase
from unittest.mock import patch

from ai_engine.agents.co_agent import generate_co_content


class COAgentTests(SimpleTestCase):
    @patch("ai_engine.agents.co_agent.validate_co_json")
    @patch("ai_engine.agents.co_agent.call_llm")
    def test_generate_co_content_success_first_try(self, call_llm_mock, validate_mock):
        call_llm_mock.return_value = """
        {
          "audio_script": "Bonjour",
          "questions": [{"question":"Q1","choices":["A","B"],"correct_answer":"A"}]
        }
        """
        data = generate_co_content("fr", "A1")
        self.assertIn("audio_script", data)
        self.assertIn("questions", data)
        validate_mock.assert_called_once()