import io
from unittest.mock import patch, Mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from ai_engine.services import availability
from ai_engine.services.llm_service import call_llm
from ai_engine.services.local_content import resume_documents, interview_question, interview_review
from ai_engine.services.learning_fallback import lesson
from ai_engine.services.official_sources import allowed, fetch, Page


class RoutingTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(AI_CONTENT_MODE='auto')
    @patch('ai_engine.services.llm_service.get_vertex_client')
    @patch('ai_engine.services.openai_adapter.call_openai', return_value='paid result')
    def test_available_credit_calls_provider_and_not_fallback(self, paid, vertex):
        fallback = Mock(return_value='local')
        self.assertEqual(call_llm('system', 'question', fallback=fallback), 'paid result')
        paid.assert_called_once()
        vertex.assert_not_called()
        fallback.assert_not_called()

    @override_settings(AI_CONTENT_MODE='auto')
    @patch('ai_engine.services.llm_service.get_genai_studio_client', return_value=(None, 'unavailable'))
    @patch('ai_engine.services.llm_service.get_vertex_client', return_value=(None, 'unavailable'))
    @patch('ai_engine.services.openai_adapter.call_openai', side_effect=RuntimeError('insufficient_quota'))
    def test_quota_falls_back_then_cooldown_prevents_repeated_billing_attempts(self, paid, vertex, studio):
        for _ in range(2):
            self.assertEqual(call_llm('s', 'u', fallback='local'), 'local')
        self.assertEqual(paid.call_count, 1)
        availability.reset()
        paid.side_effect = None
        paid.return_value = 'recharged'
        self.assertEqual(call_llm('s', 'u', fallback='local'), 'recharged')

    @override_settings(AI_CONTENT_MODE='auto')
    @patch('ai_engine.services.llm_service.get_vertex_client')
    @patch('ai_engine.services.openai_adapter.call_openai', side_effect=RuntimeError('quota'))
    def test_other_provider_is_tried_before_local(self, paid, vertex):
        client = Mock()
        client.models.generate_content.return_value.text = 'Gemini result'
        vertex.return_value = (client, None)
        self.assertEqual(call_llm('s','u',fallback='local'), 'Gemini result')

    @override_settings(AI_CONTENT_MODE='offline')
    @patch('ai_engine.services.openai_adapter.call_openai')
    @patch('ai_engine.services.llm_service.get_vertex_client')
    def test_offline_never_calls_provider(self, vertex, paid):
        self.assertEqual(call_llm('s','u',fallback='local'), 'local')
        with self.assertRaises(RuntimeError):
            call_llm('s','u')
        vertex.assert_not_called()
        paid.assert_not_called()


class LocalTests(SimpleTestCase):
    def test_cv_keeps_facts_and_escapes_html(self):
        html, letter = resume_documents('Nom : Amina\n=== EXPÉRIENCES ===\n<script>alert(1)</script>\nComptable', '', 'fr')
        self.assertIn('Comptable', html)
        self.assertNotIn('<script>', html)
        self.assertIn('Amina', letter)
        self.assertTrue(html.startswith('<!-- eshelle:local -->'))

    def test_interview_progresses_without_invented_grade(self):
        history = [{'role':'user','content':'Meine Erfahrung'}]
        self.assertNotEqual(interview_question([], 'de'), interview_question(history, 'de'))
        self.assertIn('Non évalué automatiquement', interview_review(history))

    def test_bank_has_valid_unique_answers_for_every_level(self):
        for lang in ('de','fr'):
            for level in ('A1','A2','B1','B2','C1','C2'):
                ex = lesson(lang, level, 'LESEN' if lang=='de' else 'ce')['exercises'][0]
                options = [ex['option_'+key] for key in 'abcd']
                self.assertEqual(len(set(options)), 4)
                self.assertTrue(options['ABCD'.index(ex['correct_option'])])

    def test_source_allowlist_rejects_spoofed_host_and_redirect_to_private_host(self):
        self.assertFalse(allowed('https://canada.ca.evil.test/news', ['canada.ca']))
        self.assertFalse(allowed('http://canada.ca/news', ['canada.ca']))
        response = Mock(status_code=302, headers={'Location':'http://127.0.0.1/'})
        with patch('ai_engine.services.official_sources.requests.get', return_value=response) as get:
            with self.assertRaises(ValueError):
                fetch('https://canada.ca/news', ['canada.ca'])
            self.assertEqual(get.call_count, 1)

    def test_publication_not_confused_with_modified_date_and_graph_parsed(self):
        page = Page('<meta name="dcterms.modified" content="2026-09-14"><script type="application/ld+json">{"@graph":[{"@type":"Event"}]}</script>')
        self.assertEqual(page.published, '')
        self.assertTrue(any(node.get('@type') == 'Event' for node in page.schemas))


class GenerationTests(TestCase):
    @patch('ai_engine.services.llm_service.call_llm', side_effect=RuntimeError('quota'))
    def test_cv_helpers_return_both_documents_on_quota(self, provider):
        from canada_resume.views import _call_ai_generate_canada
        from lebenslauf.views import _call_ai_generate
        for html, cover in [_call_ai_generate_canada('Nom : Amina', '', 'fr'), _call_ai_generate('Nom : Amina', '')]:
            self.assertIn('Amina', html)
            self.assertIn('Amina', cover)

    @patch('canada_resume.views.check_user_has_paid_edu_subscription', return_value=False)
    @patch('ai_engine.services.llm_service.call_llm', side_effect=RuntimeError('quota'))
    def test_canada_interview_and_coach_return_local_reply(self, provider, subscription):
        import json
        from django.contrib.auth import get_user_model
        from django.urls import reverse
        user = get_user_model().objects.create_user(username='fallback-client')
        self.client.force_login(user)
        for name, message, history in [
            ('interview_simulation_api', '', []),
            ('interview_simulation_api', 'Mon parcours', [{'role':'assistant','content':'Question'}]),
            ('immigration_coach_api', 'Mes démarches', []),
        ]:
            response = self.client.post(reverse('canada_resume:'+name),
                data=json.dumps({'message':message, 'history':history}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['mode'], 'local')
            self.assertTrue(response.json()['reply'])

    @patch('GermanPrepApp.management.commands.generate_german_content.call_llm', return_value='not JSON')
    def test_malformed_ai_lesson_uses_valid_local_bank(self, provider):
        from GermanPrepApp.models import GermanLesson
        call_command('generate_german_content', level='C1', skill='LESEN', lessons=1, sleep=0, stdout=io.StringIO())
        self.assertIn('eshelle:local', GermanLesson.objects.get().content)

    def test_german_offline_is_persisted_once_with_exercises(self):
        from GermanPrepApp.models import GermanLesson, GermanExercise
        for _ in range(2):
            call_command('generate_german_content', level='B2', skill='LESEN', lessons=3, sleep=0, stdout=io.StringIO())
        self.assertEqual(GermanLesson.objects.count(), 1)
        self.assertEqual(GermanExercise.objects.count(), 1)

    @patch('preparation_tests.management.commands.generate_tcf_content.generate_audio', side_effect=RuntimeError('offline'))
    def test_tcf_no_credit_and_no_audio_has_transcript(self, tts):
        from preparation_tests.models import CourseLesson, CourseExercise
        for _ in range(2):
            call_command('generate_tcf_content', level='A2', section='co', lessons=2, sleep=0, stdout=io.StringIO())
        self.assertEqual(CourseLesson.objects.count(), 1)
        exercise = CourseExercise.objects.get()
        self.assertIsNone(exercise.audio)
        self.assertIn('bibliothèque', exercise.instruction)

    def test_placement_offline_does_not_repeat_bank(self):
        from GermanPrepApp.models import GermanPlacementQuestion
        call_command('generate_german_placement', questions=25, stdout=io.StringIO())
        count = GermanPlacementQuestion.objects.count()
        call_command('generate_german_placement', questions=25, stdout=io.StringIO())
        self.assertGreater(count, 0)
        self.assertEqual(GermanPlacementQuestion.objects.count(), count)

    def test_placement_keeps_existing_bank_when_replacement_ai_fails(self):
        from GermanPrepApp.models import GermanPlacementQuestion
        saved = GermanPlacementQuestion.objects.create(question_text='Existing reviewed question', option_a='a', option_b='b', option_c='c', option_d='d', correct_option='A', order=1)
        call_command('generate_german_placement', questions=25, replace=True, stdout=io.StringIO())
        self.assertTrue(GermanPlacementQuestion.objects.filter(pk=saved.pk).exists())

    @override_settings(AI_CONTENT_MODE='auto')
    def test_canada_commands_fallback_even_if_client_initialization_fails(self):
        from importlib import import_module
        for name, importer in [('news','import_news'), ('scholarships','import_scholarships'), ('visitor_opps','import_visitor_opportunities')]:
            module = import_module('jobs.management.commands.fetch_canada_'+name)
            with patch.object(module.Command, '_handle_ai', side_effect=RuntimeError('client unavailable')), patch.object(module, importer, return_value={'created':1,'updated':0,'found':1}) as local:
                call_command('fetch_canada_'+name, stdout=io.StringIO())
                local.assert_called_once()

    @patch('germany_opportunities.tasks.requests.get', side_effect=__import__('requests').ConnectionError('network'))
    def test_failed_german_source_does_not_deactivate_existing_offers(self, request):
        from germany_opportunities.models import AusbildungOffer
        from germany_opportunities.tasks import fetch_ausbildung_offers
        from django.utils import timezone
        offer = AusbildungOffer.objects.create(ref_nr='preserve', title='Pflege', company='Example')
        AusbildungOffer.objects.filter(pk=offer.pk).update(last_seen=timezone.now()-timezone.timedelta(days=10))
        with self.assertRaises(RuntimeError):
            fetch_ausbildung_offers()
        offer.refresh_from_db()
        self.assertTrue(offer.is_active)

    def test_german_offer_has_local_summary_and_can_be_enriched_later(self):
        from germany_opportunities.models import AusbildungOffer
        from germany_opportunities.tasks import enrich_offers_with_ai
        offer = AusbildungOffer.objects.create(ref_nr='test1', title='Pflege', company='Example', city='Berlin')
        enrich_offers_with_ai()
        offer.refresh_from_db()
        self.assertTrue(offer.ai_summary_fr.startswith('Fiche pratique (sans IA).'))
        with patch('ai_engine.services.llm_service.call_llm', return_value='Résumé enrichi'):
            enrich_offers_with_ai()
        offer.refresh_from_db()
        self.assertEqual(offer.ai_summary_fr, 'Résumé enrichi')

    @patch('jobs.content_fallback.official_news')
    def test_news_keeps_real_date_and_existing_summary(self, source):
        from django.utils import timezone
        from jobs.content_fallback import import_news
        from jobs.models import CanadaNews
        day = timezone.localdate().isoformat()
        source.return_value = [{'url':'https://canada.ca/news/example', 'title':'Annonce', 'published':day}]
        self.assertEqual(import_news()['created'], 1)
        item = CanadaNews.objects.get()
        self.assertEqual(str(item.published_date), day)
        item.summary = 'Résumé validé'
        item.save()
        self.assertEqual(import_news()['updated'], 1)
        item.refresh_from_db()
        self.assertEqual(item.summary, 'Résumé validé')
