import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CanadaResumeAgentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="canada_agent_user",
            email="canada-agent@example.com",
            password="pass12345",
        )

    @patch("ai_engine.services.llm_service.call_llm")
    def test_immigration_coach_api_returns_ai_reply(self, call_llm):
        call_llm.return_value = "Réponse Canada OK"
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("canada_resume:immigration_coach_api"),
            data=json.dumps({
                "message": "Comment fonctionne Entrée Express ?",
                "history": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Réponse Canada OK")

    @patch("ai_engine.services.llm_service.call_llm")
    def test_interview_simulation_api_can_start_interview(self, call_llm):
        call_llm.return_value = "Bonjour, première question d'entretien."
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("canada_resume:interview_simulation_api"),
            data=json.dumps({
                "message": "",
                "history": [],
                "sector": "Santé & Soins infirmiers",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("première question", response.json()["reply"])

    @patch("ai_engine.services.llm_service.call_llm", return_value="• Gérer les commandes.")
    def test_improve_description_returns_provider_output(self, provider):
        self.client.force_login(self.user)
        response = self.client.post(reverse("canada_resume:improve_description_api"),
            data=json.dumps({"text": "Je gere les commandes"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["improved_text"], "• Gérer les commandes.")

    @patch("ai_engine.services.llm_service.call_llm", return_value="<h1>CV</h1>=== ANSCHREIBEN_START ===Lettre")
    def test_resume_and_cover_letter_are_split(self, provider):
        from .views import _call_ai_generate_canada
        self.assertEqual(_call_ai_generate_canada("Profil de test", "Offre de test", "fr"),
                         ("<h1>CV</h1>", "Lettre"))

    @patch("ai_engine.services.llm_service.call_llm", return_value="Plan de préparation de test.")
    def test_diagnostic_saves_generated_roadmap(self, provider):
        from .models import CanadaImmigrationProfile
        self.client.force_login(self.user)
        response = self.client.post(reverse("canada_resume:diagnostic"), data={
            "age": 29, "education_level": "bachelor", "work_experience_years": 3,
            "tcf_level": "B2",
        })
        self.assertEqual(response.status_code, 302)
        from .guidance import ROADMAP_PREFIX
        self.assertEqual(CanadaImmigrationProfile.objects.get(user=self.user).ai_roadmap,
                         ROADMAP_PREFIX + "Plan de préparation de test.")
