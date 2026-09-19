import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import EESubmission, UserExerciseProgress
from .services.learning_coach import normalize_feedback, evaluate_production, learning_dashboard
from .tests import FrenchTcfAgentsTests
from .views_mock_exam_format import _calc_score, EXAM_CONFIGS


def example_feedback():
    return {
        "feedback": "L'idée est claire ; développe une raison et un exemple.",
        "criteria": {"task": 65, "coherence": 50, "grammar": 70, "vocabulary": 60},
        "strengths": ["Une proposition identifiable."], "errors": [],
        "corrected_version": "Je propose une bibliothèque.",
        "priorities": [{"category": "coherence", "evidence": "Je propose une bibliothèque.",
            "diagnosis": "Une proposition sans justification.",
            "action": "Ajoute une raison puis un exemple concret.",
            "drill": "Écris deux phrases pour justifier l'utilité de cette bibliothèque.",
            "success_check": "Une raison, un exemple précis et un lien clair avec la proposition."}],
        "model_example": "Une bibliothèque offrirait notamment un espace de travail aux habitants.",
        "next_attempt": "Réécris ta réponse avec un argument développé.",
    }


class LearningFeedbackTests(SimpleTestCase):
    def test_evidence_and_action_are_preserved_and_grade_is_derived(self):
        result = normalize_feedback(example_feedback(), "Je propose une bibliothèque.", "ee")
        self.assertEqual(result["score"], 61)
        self.assertIn("drill", result["coaching"]["priorities"][0])
        self.assertIn("sans équivalence", result["coaching"]["assessment_note"])

    def test_missing_invalid_and_nonfinite_scores_are_rejected(self):
        for value in (None, True, "80", float("nan"), float("inf"), 101, -1):
            raw = example_feedback()
            raw["criteria"]["task"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_feedback(raw, "Je propose une bibliothèque.", "ee")

    def test_invented_evidence_cannot_be_presented_as_student_text(self):
        with self.assertRaises(ValueError):
            normalize_feedback(example_feedback(), "Autre texte.", "ee")

    def test_missing_element_can_be_explained_without_fabricating_a_quote(self):
        raw = example_feedback()
        raw["priorities"][0]["evidence"] = ""
        self.assertTrue(normalize_feedback(raw, "Autre texte.", "ee")["coaching"]["priorities"])

    def test_off_topic_answer_cannot_pass_on_style_alone(self):
        raw = example_feedback()
        raw["criteria"] = {"task": 10, "coherence": 95, "grammar": 95, "vocabulary": 95}
        self.assertLess(normalize_feedback(raw, "Je propose une bibliothèque.", "ee")["score"], 40)

    def test_oral_rubric_does_not_score_pronunciation_from_text(self):
        result = normalize_feedback(example_feedback(), "Je propose une bibliothèque.", "eo")
        self.assertNotIn("pronunciation", result["criteria"])
        self.assertIn("ne sont pas notées", result["coaching"]["assessment_note"])

    @override_settings(OPENAI_API_KEY="")
    @patch("ai_engine.services.eval_service._call_anthropic_eval_json")
    @patch("ai_engine.services.eval_service._call_gemini_eval_json", return_value={"score": 99})
    def test_invalid_provider_output_tries_the_next_provider(self, gemini, anthropic):
        anthropic.return_value = example_feedback()
        result = evaluate_production("Je propose une bibliothèque.", "Sujet", "Consigne", "B2", "ee")
        self.assertEqual(result["score"], 61)
        anthropic.assert_called_once()

    def test_training_percentages_never_become_official_c2_scores(self):
        for exam in ("tcf", "tef"):
            result = _calc_score(exam, 10, 10, 10, 10)
            self.assertEqual(result["global"], 100)
            self.assertEqual(result["global_max"], 100)
            self.assertEqual(result["cefr_global"], "—")
            self.assertIsNone(result["passed"])
        self.assertEqual(EXAM_CONFIGS["tcf"]["co_count"], 39)
        self.assertEqual(EXAM_CONFIGS["tef"]["ce_count"], 40)
        from .views_level_mock import _estimate_cefr
        self.assertEqual(_estimate_cefr(100, "A1"), "A1")
        self.assertEqual(_estimate_cefr(100), "—")


class LearningJourneyTests(TestCase):
    setUp = FrenchTcfAgentsTests.setUp
    _lesson = FrenchTcfAgentsTests._lesson
    _exercise = FrenchTcfAgentsTests._exercise

    def post_answer(self, text="Je propose une bibliothèque."):
        return self.client.post(reverse("preparation_tests:submit_ee"),
            data=json.dumps({"exercise_id": self.ee_exercise.pk, "text": text}),
            content_type="application/json")

    @patch("ai_engine.services.eval_service.evaluate_ee")
    def test_second_attempt_receives_only_this_students_previous_answer(self, evaluate):
        other = get_user_model().objects.create_user(username="other-student")
        EESubmission.objects.create(user=other, exercise=self.ee_exercise, text="Private other answer", score=99)
        evaluate.side_effect = lambda **kwargs: normalize_feedback(example_feedback(), "Je propose une bibliothèque.", "ee")
        first = self.post_answer()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(evaluate.call_args.kwargs["coaching_context"]["previous"], {})
        second = self.post_answer()
        self.assertEqual(second.status_code, 200)
        previous = evaluate.call_args.kwargs["coaching_context"]["previous"]
        self.assertEqual(previous["text"], "Je propose une bibliothèque.")
        self.assertEqual(second.json()["coaching"]["comparison"]["change"], 0)
        self.assertEqual(EESubmission.objects.filter(user=self.user).count(), 2)

    def test_dashboard_is_private_and_does_not_mark_a_target_as_achieved(self):
        other = get_user_model().objects.create_user(username="private-student")
        EESubmission.objects.create(user=other, exercise=self.ee_exercise, text="Private", score=99,
                                   feedback_json={"feedback": "Private report"})
        response = self.client.get(reverse("preparation_tests:learning_center"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Objectif C2")
        self.assertNotContains(response, "Private report")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("preparation_tests:learning_center")).status_code, 302)

    def test_saved_answer_is_restored_for_its_author_only(self):
        EESubmission.objects.create(user=self.user, exercise=self.ee_exercise, score=62,
            text="Mon texte personnel", feedback_json={"feedback": "Retour personnel"})
        url = reverse("preparation_tests:lesson_session", args=["tcf", "ee", self.ee_lesson.id])
        self.assertContains(self.client.get(url), "Mon texte personnel")
        self.client.logout()
        self.assertNotContains(self.client.get(url), "Mon texte personnel")

    def test_qcm_progress_is_verified_on_server(self):
        exercise = self.ce_lesson.exercises.first()
        response = self.client.post(reverse("preparation_tests:exercise_progress"),
            data=json.dumps({"exercise_id": exercise.pk, "selected": "B", "correct": True}),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserExerciseProgress.objects.get(user=self.user, exercise=exercise).is_completed)

    @patch("ai_engine.services.llm_service.call_llm", return_value="Repère l'indice dans le texte.")
    def test_qcm_explanation_uses_the_reference_answer_and_caches_public_content(self, provider):
        cache.clear()
        exercise = self.ce_lesson.exercises.first()
        for _ in range(2):
            response = self.client.post(reverse("preparation_tests:explain_answer"),
                data=json.dumps({"exercise_id": exercise.pk, "selected": "B", "correct": "D"}),
                content_type="application/json")
            self.assertEqual(response.json()["correct_option"], "A")
            self.assertFalse(response.json()["is_correct"])
        provider.assert_called_once()

    def test_level_preference_changes_recommendations(self):
        self.client.post(reverse("preparation_tests:learning_center"), {"target_level": "C2"})
        response = self.client.get(reverse("preparation_tests:learning_center"))
        self.assertEqual(response.context["target_level"], "C2")
        self.assertTrue(all(item["lesson"] is None for item in response.context["next_lessons"]))

    def test_completed_lesson_is_not_recommended_before_a_new_lesson(self):
        from .models import CourseLesson, UserLessonProgress
        second = CourseLesson.objects.create(exam=self.exam, section="ee", level="B2",
            title="Prochaine leçon", slug="next-lesson", is_published=True, order=2)
        second.exams.add(self.exam)
        self._exercise(second, "Un autre sujet")
        UserLessonProgress.objects.create(user=self.user, lesson=self.ee_lesson, is_completed=True)
        dashboard = learning_dashboard(self.user)
        selected = next(item for item in dashboard["next_lessons"] if item["skill"] == "EE")
        self.assertEqual(selected["lesson"].pk, second.pk)

    def test_canada_page_has_sources_and_no_invented_crs(self):
        response = self.client.get(reverse("canada_resume:diagnostic"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "25 mars 2025")
        self.assertNotContains(response, "460 et 510")
        self.assertNotContains(response, "Votre Score CRS Estimé")

    def test_obsolete_crs_calculator_does_not_return_a_score(self):
        from canada_resume.views import _calculate_crs
        self.assertIsNone(_calculate_crs(28, "bachelor", 3, "C2", True))

    def test_wrong_skill_and_oversized_production_are_rejected(self):
        self.assertEqual(self.post_answer("x" * 15001).status_code, 400)
        response = self.client.post(reverse("preparation_tests:submit_ee"),
            data=json.dumps({"exercise_id": self.eo_exercise.pk, "text": "Bonjour."}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EESubmission.objects.exists())

    @patch("ai_engine.services.eval_service.evaluate_ee")
    def test_selected_tef_context_is_preserved_for_shared_lesson(self, provider):
        provider.return_value = normalize_feedback(example_feedback(), "Je propose une bibliothèque.", "ee")
        response = self.client.post(reverse("preparation_tests:submit_ee"),
            data=json.dumps({"exercise_id": self.ee_exercise.pk, "text": "Je propose une bibliothèque.", "exam": "tef"}),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(provider.call_args.kwargs["coaching_context"]["exam"], "tef")

    @patch("ai_engine.services.llm_service.call_llm", return_value="Entraînement TEF proposé.")
    def test_chat_uses_the_selected_exam_and_avoids_official_score_promises(self, provider):
        session = self.client.session
        session["french_learning_exam"] = "tef"
        session.save()
        response = self.client.post(reverse("preparation_tests:ai_coach_api"),
            data=json.dumps({"message": "Propose un exercice", "history": []}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        prompt = provider.call_args.args[0]
        self.assertIn("Examen sélectionné : TEF", prompt)
        self.assertNotIn("numéro 1 mondial", prompt)

    def test_legacy_grades_are_not_compared_to_the_new_rubric(self):
        from .services.learning_coach import add_comparison
        result = normalize_feedback(example_feedback(), "Je propose une bibliothèque.", "ee")
        add_comparison(result, {"score": 80})
        self.assertNotIn("comparison", result["coaching"])

    def test_chat_rejects_authenticated_requests_without_csrf_token(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(reverse("preparation_tests:ai_coach_api"),
            data=json.dumps({"message": "Bonjour", "history": []}),
            content_type="application/json")
        self.assertEqual(response.status_code, 403)
