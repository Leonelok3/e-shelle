import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from .models import ImmigrationJourney, ImmigrationAIUsage, LearningDraft
from .assessment import QUESTIONS
from .ai_budget import ai_budget
from preparation_tests.models import Exam, CourseLesson, CourseExercise


class JourneyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='learner')
        self.other = get_user_model().objects.create_user(username='other')
        self.client.force_login(self.user)

    def create_journey(self):
        return ImmigrationJourney.objects.create(user=self.user)

    def test_onboarding_persists_and_dashboard_renders(self):
        response = self.client.post(reverse('immigration97:onboarding'), {
            'goal': 'language', 'exam': 'tcf', 'working_level': 'A2',
            'target_level': 'B2', 'daily_minutes': 20})
        self.assertRedirects(response, reverse('immigration97:assessment'))
        self.assertEqual(ImmigrationJourney.objects.get(user=self.user).daily_minutes, 20)
        self.assertEqual(self.client.get(reverse('immigration97:dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('immigration97:dossier')).status_code, 200)

    def test_invalid_target_does_not_create_profile(self):
        self.client.post(reverse('immigration97:onboarding'), {
            'goal': 'language', 'exam': 'tcf', 'working_level': 'B2',
            'target_level': 'A1', 'daily_minutes': 20})
        self.assertFalse(ImmigrationJourney.objects.exists())

    def test_assessment_is_scored_on_server_and_applied_separately(self):
        journey = self.create_journey()
        answers = {key: str(correct) for key, _, _, correct, _ in QUESTIONS}
        answers['suggested_level'] = 'C2'
        response = self.client.post(reverse('immigration97:assessment'), answers)
        self.assertEqual(response.status_code, 200)
        journey.refresh_from_db()
        self.assertEqual(journey.assessment['suggested_level'], 'B2')
        self.assertEqual(journey.working_level, 'A2')
        self.client.post(reverse('immigration97:apply_assessment'))
        journey.refresh_from_db()
        self.assertEqual(journey.working_level, 'B2')

    def test_checklist_is_private_and_rejects_unknown_tasks(self):
        journey = self.create_journey()
        other = ImmigrationJourney.objects.create(user=self.other)
        self.client.post(reverse('immigration97:checklist_update'), {'task': 'cv', 'done': '1'})
        self.client.post(reverse('immigration97:checklist_update'), {'task': 'unexpected', 'done': '1'})
        journey.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(journey.checklist, {'cv': True})
        self.assertEqual(other.checklist, {})

    def test_drafts_are_private_and_validate_content(self):
        exam = Exam.objects.create(code='tcf', name='TCF', language='fr')
        lesson = CourseLesson.objects.create(exam=exam, section='ee', level='A2',
            title='Writing', slug='writing', is_published=True)
        exercise = CourseExercise.objects.create(lesson=lesson, title='Essay', is_active=True)
        url = reverse('immigration97:draft', args=[exercise.pk])
        response = self.client.post(url, json.dumps({'text': 'Mon brouillon'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(url).json()['text'], 'Mon brouillon')
        self.assertEqual(self.client.post(url, json.dumps({'text': 'x' * 15001}), content_type='application/json').status_code, 400)
        self.client.force_login(self.other)
        self.assertFalse(self.client.get(url).json()['exists'])
        self.assertEqual(LearningDraft.objects.get(user=self.user).text, 'Mon brouillon')

    @override_settings(IMMIGRATION97_DAILY_AI_LIMIT=2)
    def test_quota_persists_across_requests_and_invalid_input_is_refunded(self):
        factory = RequestFactory()
        def call(status=200):
            request = factory.post('/')
            request.user = self.user
            return ai_budget(lambda request: JsonResponse({}, status=status))(request)
        self.assertEqual(call(400).status_code, 400)
        self.assertEqual(ImmigrationAIUsage.objects.get(user=self.user).attempts, 0)
        self.assertEqual(call().status_code, 200)
        self.assertEqual(call().status_code, 200)
        self.assertEqual(call().status_code, 429)

    def test_mutations_require_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('immigration97:checklist_update'), {'task': 'cv'}).status_code, 403)
