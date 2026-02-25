from unittest.mock import patch

from django.test import SimpleTestCase

from ai_engine.agents.eo_agent import generate_eo_content


class EOAgentTests(SimpleTestCase):
    @patch("ai_engine.agents.eo_agent.validate_eo_json")
    @patch("ai_engine.agents.eo_agent.call_llm")
    def test_generate_eo_content_success_first_try(self, call_llm_mock, validate_mock):
        call_llm_mock.return_value = """
        {
          "topic": "Se présenter",
          "instructions": "Parlez de vous pendant 2 minutes.",
          "expected_points": ["identité", "profession", "objectifs"]
        }
        """
        data = generate_eo_content("fr", "A2")
        self.assertIn("topic", data)
        self.assertIn("instructions", data)
        self.assertIn("expected_points", data)
        validate_mock.assert_called_once()