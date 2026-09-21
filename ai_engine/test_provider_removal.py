"""Provider migration contracts. No network, user data or outbound messages."""
import json
import io
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from ai_engine.services.availability import reset
from ai_engine.services.llm_service import call_llm, stream_llm


def openai_chunk(text='', usage=None):
    return NS(model='gpt-test', usage=usage,
              choices=[NS(delta=NS(content=text))] if text else [])


@override_settings(AI_CONTENT_MODE='auto', OPENAI_API_KEY='test-only',
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class ProviderMigrationTests(SimpleTestCase):
    def setUp(self):
        reset()

    @patch('ai_engine.services.openai_adapter._client')
    def test_openai_stream_retains_text_usage_and_actual_model(self, factory):
        factory.return_value.chat.completions.create.return_value = iter([
            openai_chunk('Bonjour'), openai_chunk(' !'),
            openai_chunk(usage=NS(prompt_tokens=12, completion_tokens=3)),
        ])
        usage = {}
        self.assertEqual(''.join(stream_llm('s', 'u', usage=usage)), 'Bonjour !')
        self.assertEqual(usage, {'model': 'gpt-test', 'input_tokens': 12, 'output_tokens': 3})

    @patch('ai_engine.services.llm_service.get_vertex_client')
    @patch('ai_engine.services.openai_adapter._client', return_value=None)
    def test_stream_uses_gemini_when_openai_is_not_configured(self, openai, vertex):
        client = Mock()
        client.models.generate_content_stream.return_value = iter([
            NS(text='Gemini OK', model_version='gemini-test',
               usage_metadata=NS(prompt_token_count=8, candidates_token_count=2))])
        vertex.return_value = (client, None)
        usage = {}
        self.assertEqual(list(stream_llm('s', 'u', usage=usage)), ['Gemini OK'])
        self.assertEqual(usage['model'], 'gemini-test')

    @patch('ai_engine.services.llm_service.get_vertex_client')
    @patch('ai_engine.services.openai_adapter._client')
    def test_partial_stream_failure_never_appends_a_different_answer(self, openai, vertex):
        def broken():
            yield openai_chunk('Partial')
            raise RuntimeError('provider disconnected')
        openai.return_value.chat.completions.create.return_value = broken()
        stream = stream_llm('s', 'u', usage={})
        self.assertEqual(next(stream), 'Partial')
        with self.assertRaises(RuntimeError):
            next(stream)
        vertex.assert_not_called()

    @patch('ai_engine.services.openai_adapter._client')
    def test_non_streaming_metadata_preserves_real_token_counts(self, factory):
        factory.return_value.chat.completions.create.return_value = NS(
            model='gpt-test', choices=[NS(message=NS(content='OK'))],
            usage=NS(prompt_tokens=9, completion_tokens=1))
        usage = {}
        self.assertEqual(call_llm('s', 'u', usage=usage), 'OK')
        self.assertEqual(usage['input_tokens'], 9)

    @patch('ai_engine.views.GenerationIA.objects.create')
    @patch('ai_engine.views.stream_llm')
    def test_generator_preserves_sse_contract_and_history(self, provider, save):
        from ai_engine.views import stream_generate
        def fake(*args, usage, **kwargs):
            usage.update(model='gemini-test', input_tokens=5, output_tokens=2)
            yield 'Bonjour'
        provider.side_effect = fake
        request = RequestFactory().post('/ai/stream/', json.dumps({'prompt': 'Test'}),
                                        content_type='application/json')
        request.user = NS(is_authenticated=True)
        response = stream_generate(request)
        body = b''.join(response.streaming_content).decode()
        self.assertIn('"chunk": "Bonjour"', body)
        self.assertIn('"done": true', body)
        self.assertEqual(save.call_args.kwargs['modele'], 'gemini-test')
        self.assertEqual(save.call_args.kwargs['tokens_output'], 2)

    @patch('ai_engine.views.GenerationIA.objects.create')
    @patch('ai_engine.views.stream_llm', side_effect=RuntimeError('sensitive-provider-details'))
    def test_generator_failure_is_saved_without_exposing_provider_details(self, provider, save):
        from ai_engine.views import stream_generate
        request = RequestFactory().post('/ai/stream/', json.dumps({'prompt': 'Test'}),
                                        content_type='application/json')
        request.user = NS(is_authenticated=True)
        body = b''.join(stream_generate(request).streaming_content).decode()
        self.assertNotIn('sensitive-provider-details', body)
        self.assertEqual(save.call_args.kwargs['statut'], 'erreur')

    @patch('whatsapp_agent.services.call_llm')
    def test_whatsapp_generation_keeps_text_and_list_contracts(self, provider):
        from whatsapp_agent.services import WhatsAppService
        provider.return_value = 'Message de test'
        self.assertEqual(WhatsAppService.generer_message_ia('test', 'test'), 'Message de test')
        provider.return_value = '["Message A", "Message B"]'
        self.assertEqual(WhatsAppService.generer_variations_multiples_ia('test', 'test', 2),
                         ['Message A', 'Message B'])
        provider.side_effect = RuntimeError('offline')
        self.assertTrue(WhatsAppService.generer_variations_multiples_ia('test', 'test'))

    @patch('facebook_agent.agents.call_llm')
    def test_facebook_generation_tracks_usage_without_publishing(self, provider):
        from facebook_agent.agents import BaseAgent
        def fake(*args, usage, **kwargs):
            usage.update(model='gemini-test', input_tokens=5, output_tokens=4)
            return 'Brouillon'
        provider.side_effect = fake
        agent = BaseAgent('general')
        self.assertEqual(agent.generate_content('Test'), 'Brouillon')
        self.assertEqual(agent.tokens_used, 9)

    @override_settings(GCP_VERTEX_KEY_PATH='', GOOGLE_API_KEY='')
    @patch('ai_engine.services.openai_adapter.call_openai')
    def test_adgen_can_generate_json_using_openai_without_google(self, provider):
        from adgen.services.ai_service import AdGenAIService
        def fake(*args, usage, **kwargs):
            usage.update(model='gpt-test', input_tokens=5, output_tokens=4)
            return '{"title":"Test"}'
        provider.side_effect = fake
        result = AdGenAIService().generate({'nom_produit': 'Test'}, [])
        self.assertEqual(result['generation_model'], 'gpt-test')
        self.assertEqual(result['_tokens_used'], 9)

    @patch('ai_engine.services.llm_service.call_llm', return_value='{"title":"Test"}')
    def test_business_slide_keeps_json_response(self, provider):
        from business.views import api_generate_slide_ai
        request = RequestFactory().post('/test/', json.dumps({'prompt': 'Test'}),
                                        content_type='application/json')
        request.user = NS(is_active=True, is_staff=True)
        result = api_generate_slide_ai(request)
        self.assertEqual(json.loads(result.content)['slide']['title'], 'Test')

    @patch('ai_engine.services.llm_service.call_llm', side_effect=RuntimeError('offline'))
    def test_commercial_agent_keeps_local_fallback(self, provider):
        from commercial_agent.services import CommercialAgentService
        prospect = NS(module='services', plan_recommande='starter', responsable='Amina',
                      nom='Test', ville='Douala')
        self.assertIn('Amina', CommercialAgentService.generate_message(prospect))

    @patch('ai_engine.services.llm_service.call_llm')
    def test_math_commands_preserve_generated_records(self, provider):
        from math_cm.management.commands import generate_cours, generate_exercices
        chapter = NS(slug='test', titre='Test', classe=NS(label='Sixième'),
                     exercices=Mock())
        chapter.exercices.count.return_value = 0
        with patch.object(generate_cours.Chapitre.objects, 'get', return_value=chapter), \
             patch.object(generate_cours.Lecon.objects, 'filter') as existing, \
             patch.object(generate_cours.Lecon.objects, 'update_or_create', return_value=(None, True)) as save:
            existing.return_value.exclude.return_value.exists.return_value = False
            provider.return_value = json.dumps([{'ordre': 1, 'titre': 'Test', 'contenu': {'sections': []}}])
            generate_cours.Command(stdout=io.StringIO()).handle(chapitre='test', lecons=1)
            self.assertEqual(save.call_args.kwargs['defaults']['titre'], 'Test')
        with patch.object(generate_exercices.Chapitre.objects, 'get', return_value=chapter), \
             patch.object(generate_exercices.Exercice.objects, 'update_or_create') as save:
            provider.return_value = json.dumps([{'titre': 'Test', 'enonce': '2+2', 'correction': '4'}])
            generate_exercices.Command(stdout=io.StringIO()).handle(chapitre='test', niveau='entrainement', nb=1)
            self.assertEqual(save.call_args.kwargs['defaults']['correction'], '4')
