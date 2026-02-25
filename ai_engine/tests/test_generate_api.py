import json
from unittest.mock import patch

from django.test import SimpleTestCase


class GenerateApiTests(SimpleTestCase):
    @patch("ai_engine.api_views.generate_and_insert")
    def test_generate_api_success(self, orchestrator_mock):
        orchestrator_mock.return_value = {"inserted": False, "skill": "CE"}

        response = self.client.post(
            "/api/ai/generate/",
            data=json.dumps({"skill": "CE", "language": "fr", "level": "A1"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["result"]["skill"], "CE")

    def test_generate_api_missing_fields(self):
        response = self.client.post(
            "/api/ai/generate/",
            data=json.dumps({"skill": "CE"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_generate_api_get_help(self):
        response = self.client.get("/api/ai/generate/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("Use POST", data["message"])