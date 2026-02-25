from unittest.mock import patch
from django.test import SimpleTestCase

from ai_engine.services.generation_orchestrator import generate_and_insert


class GenerationOrchestratorTests(SimpleTestCase):
    @patch("ai_engine.services.generation_orchestrator.generate_ce_content")
    def test_generate_and_insert_ce(self, gen_mock):
        gen_mock.return_value = {
            "title": "CE A1 - Texte court",
            "skill": "CE",
            "level": "A1",
            "language": "fr",
            "content": {"reading_text": "Texte"},
            "questions": [{"question": "Q1", "choices": ["A", "B"], "correct_answer": "A"}],
        }

        result = generate_and_insert(skill="CE", language="fr", level="A1")
        self.assertEqual(result["inserted"], False)
        self.assertEqual(result["skill"], "CE")