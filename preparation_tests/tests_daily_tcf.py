import copy
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, Client, override_settings
from django.urls import reverse
from django.utils.html import escape
from preparation_tests.services.daily_tcf import daily_session, daily_audio_name, grade_questions
from preparation_tests.services.daily_tcf_bank import TOPICS
from preparation_tests.views_daily_tcf import STATE_KEY


class DailyBankTests(SimpleTestCase):
    def test_twenty_eight_day_rotation_is_deterministic_and_does_not_mutate_bank(self):
        before = copy.deepcopy(TOPICS)
        days = [daily_session(date(2026, 10, 1) + timedelta(days=i)) for i in range(28)]
        self.assertEqual(len({(day["skill"], day["topic"]) for day in days}), 28)
        self.assertEqual(len({day["lesson_title"] for day in days}), 28)
        self.assertEqual({day["skill"] for day in days}, {"ce", "co", "ee", "eo"})
        self.assertEqual(daily_session(date(2026, 10, 29))["topic"], days[0]["topic"])
        self.assertEqual(daily_session(date(2026, 10, 1)), daily_session(date(2026, 10, 1)))
        self.assertEqual(TOPICS, before)

    def test_all_qcm_have_four_distinct_choices_and_exact_document_evidence(self):
        for topic in TOPICS:
            for skill in ("ce", "co"):
                document = topic[skill]["document"]
                self.assertGreater(len(document.split()), 70)
                for question in topic[skill]["questions"]:
                    self.assertEqual(set(question["options"]), set("ABCD"))
                    self.assertEqual(len(set(question["options"].values())), 4)
                    self.assertIn(question["answer"], question["options"])
                    self.assertIn(question["evidence"], document)

    def test_grade_uses_server_keys_after_daily_option_shuffle(self):
        day = daily_session(date(2026, 10, 1))
        answers = {str(i): q["answer"] for i, q in enumerate(day["questions"])}
        self.assertEqual(grade_questions(day, answers)["correct"], 3)
        self.assertEqual(grade_questions(day, {})["correct"], 0)

    def test_writing_word_limits_and_oral_duration_match_isolated_tasks(self):
        tasks = set()
        for i in range(28):
            day = daily_session(date(2026, 10, 1) + timedelta(days=i))
            if day["skill"] == "ee":
                tasks.add(day["task_number"])
                self.assertEqual((day["word_min"], day["word_max"]), {1: (60, 120), 2: (120, 150), 3: (120, 180)}[day["task_number"]])
                if day["task_number"] == 3:
                    self.assertIn("Document 1", day["document"])
                    self.assertIn("Document 2", day["document"])
            if day["skill"] == "eo":
                self.assertEqual(day["duration"], 270)
                self.assertEqual(day["task_number"], 3)
        self.assertEqual(tasks, {1, 2, 3})

    @override_settings(MEDIA_ROOT="unused")
    @patch("preparation_tests.management.commands.prepare_tcf_daily_audio.generate_audio")
    def test_audio_preparation_has_seven_unique_scripts(self, generate):
        from io import StringIO
        call_command("prepare_tcf_daily_audio", stdout=StringIO())
        self.assertEqual(generate.call_count, 7)
        self.assertEqual(len({call.args[0] for call in generate.call_args_list}), 7)


class DailyViewTests(TestCase):
    def setUp(self):
        self.day = date(2026, 10, 1)
        self.date_patch = patch("preparation_tests.services.daily_tcf.timezone.localdate", side_effect=lambda: self.day)
        self.date_patch.start()
        self.addCleanup(self.date_patch.stop)
        self.url = reverse("preparation_tests:tcf_daily")

    def start(self):
        return self.client.post(self.url, {"day": self.day.isoformat(), "action": "start"})

    def test_hub_card_and_lesson_render_without_provider_calls(self):
        with patch("ai_engine.services.llm_service.call_llm") as llm:
            response = self.client.get(reverse("preparation_tests:tcf_hub"))
            self.assertContains(response, "Faire ma séance du jour")
            self.assertContains(self.client.get(self.url), "La leçon du jour")
            llm.assert_not_called()

    def test_answer_keys_and_script_are_not_in_active_exam(self):
        self.start()
        response = self.client.get(self.url)
        self.assertNotIn("answer", response.context["daily"]["questions"][0])
        self.assertNotIn("evidence", response.context["daily"]["questions"][0])
        self.assertContains(response, "daily-timer")

    def test_grading_is_revealed_only_after_a_started_attempt(self):
        self.assertEqual(self.client.post(self.url, {"day": self.day.isoformat(), "action": "submit"}).status_code, 400)
        self.start()
        day = daily_session(self.day)
        payload = {"day": self.day.isoformat(), "action": "submit"}
        payload.update({f"answer_{i}": q["answer"] for i, q in enumerate(day["questions"])})
        response = self.client.post(self.url, payload, follow=True)
        self.assertContains(response, "3 / 3 réponses correctes")
        self.assertContains(response, escape(day["questions"][0]["evidence"]))
        self.assertEqual(self.client.session["tcf_daily_completed"], [self.day.isoformat()])

    def test_stale_date_is_rejected_and_new_day_starts_fresh(self):
        self.start()
        self.day = date(2026, 10, 3)
        response = self.client.post(self.url, {"day": "2026-10-01", "action": "submit", "production": "Mon texte à conserver."})
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "Mon texte à conserver.", status_code=409)
        self.assertFalse(self.client.get(self.url).context["active"])

    def test_audio_unavailable_blocks_exam_without_reading_script(self):
        self.day = date(2026, 10, 2)
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.assertEqual(self.start().status_code, 409)
            response = self.client.get(self.url)
            self.assertNotContains(response, daily_session(self.day)["document"])

    def test_audio_is_available_once_per_attempt_and_script_after_submit(self):
        self.day = date(2026, 10, 2)
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            day = daily_session(self.day)
            file = Path(directory) / daily_audio_name(day["document"])
            file.parent.mkdir(parents=True)
            file.write_bytes(b"test audio")
            self.start()
            self.assertNotContains(self.client.get(self.url), day["document"])
            self.assertEqual(self.client.post(self.url, {"day": self.day.isoformat(), "action": "audio-play"}).status_code, 200)
            self.assertEqual(self.client.post(self.url, {"day": self.day.isoformat(), "action": "audio-play"}).status_code, 409)
            response = self.client.post(self.url, {"day": self.day.isoformat(), "action": "submit"}, follow=True)
            self.assertContains(response, "Transcription du document sonore")

    def test_oral_transcript_can_be_added_after_timer_without_changing_elapsed(self):
        self.day = date(2026, 10, 4)
        self.start()
        self.client.post(self.url, {"day": self.day.isoformat(), "action": "submit"})
        elapsed = self.client.session[STATE_KEY]["elapsed"]
        self.client.post(self.url, {"day": self.day.isoformat(), "action": "transcript", "production": "Mon avis est clair."})
        self.assertEqual(self.client.session[STATE_KEY]["elapsed"], elapsed)
        self.assertEqual(self.client.session[STATE_KEY]["production"], "Mon avis est clair.")

    def test_ai_requires_login_and_keeps_response_when_provider_fails(self):
        self.day = date(2026, 10, 3)
        self.start()
        text = "Je propose de participer à cette visite avec un ami samedi matin."
        self.client.post(self.url, {"day": self.day.isoformat(), "action": "submit", "production": text})
        correction = reverse("preparation_tests:tcf_daily_correction")
        self.assertEqual(self.client.post(correction).status_code, 302)
        user = get_user_model().objects.create_user(username="daily-user", password="test-password")
        # Preserve the anonymous attempt across authentication by copying the state.
        state = dict(self.client.session[STATE_KEY])
        self.client.force_login(user)
        session = self.client.session
        session[STATE_KEY] = state
        session.save()
        with patch("preparation_tests.services.learning_coach.evaluate_production", side_effect=RuntimeError("offline")):
            self.assertEqual(self.client.post(correction).status_code, 503)
        self.assertEqual(self.client.session[STATE_KEY]["production"], text)

    def test_cached_ai_feedback_does_not_consume_budget_again(self):
        from canada_resume.models import ImmigrationAIUsage
        self.day = date(2026, 10, 3)
        user = get_user_model().objects.create_user(username="daily-cache", password="test-password")
        self.client.force_login(user)
        self.start()
        self.client.post(self.url, {"day": self.day.isoformat(), "action": "submit", "production": "Je propose de participer à cette visite avec un ami samedi matin."})
        correction = reverse("preparation_tests:tcf_daily_correction")
        with patch("preparation_tests.services.learning_coach.evaluate_production", return_value={"feedback": "Une idée claire", "coaching": {}}) as evaluate:
            self.assertEqual(self.client.post(correction).status_code, 200)
            self.assertEqual(self.client.post(correction).status_code, 200)
            evaluate.assert_called_once()
        self.assertEqual(ImmigrationAIUsage.objects.get(user=user).attempts, 1)

    def test_csrf_is_required_for_start(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url, {"day": self.day.isoformat(), "action": "start"}).status_code, 403)
