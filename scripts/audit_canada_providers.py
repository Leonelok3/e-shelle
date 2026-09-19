"""Read-only provider smoke test; never prints keys or accesses application data."""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_cm.settings')
logging.disable(logging.CRITICAL)

from django.conf import settings

# Resolve LazySettings before temporary overrides, so local provider keys load.
_ = settings.SECRET_KEY
import django
django.setup()


def probe(name, callback):
    try:
        result = callback()
        print(name, 'OK' if result else 'EMPTY', flush=True)
    except Exception as exc:
        # Provider exception messages can include credentials or request details.
        status = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
        print(name, type(exc).__name__, 'status=' + str(status), flush=True)


if __name__ == '__main__':
    if '--clients' in sys.argv:
        from e_shelle_ai.services.tools.google_media_generator import get_vertex_client, get_genai_studio_client
        for factory in (get_genai_studio_client, get_vertex_client, get_genai_studio_client):
            client, error = factory()
            safe_error = str(error)
            for name in ('OPENAI_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_SEARCH_API_KEY', 'ANTHROPIC_API_KEY'):
                value = getattr(settings, name, '') or os.getenv(name, '')
                if value:
                    safe_error = safe_error.replace(value, '[REDACTED]')
            print(factory.__name__, bool(client), safe_error, flush=True)
        sys.exit(0)

    if '--audio' in sys.argv:
        import tempfile
        from django.test import override_settings
        from ai_engine.services.tts_service import generate_audio
        from ai_engine.services.eval_service import transcribe_audio

        def audio_round_trip():
            with tempfile.TemporaryDirectory(prefix='canada-ai-audit-') as folder:
                with override_settings(MEDIA_ROOT=folder):
                    relative = generate_audio('Bonjour, je souhaite apprendre le français pour préparer mon examen.',
                                              language='fr', output_dir='audit')
                    transcript = transcribe_audio(str(Path(folder) / relative), language='fr')
                    print('Synthetic test transcript:', repr(transcript), flush=True)
                    return 'bonjour' in transcript.lower() and 'examen' in transcript.lower()

        probe('French audio synthesis and transcription (real providers)', audio_round_trip)
        sys.exit(0)

    if '--oral' in sys.argv or '--written' in sys.argv:
        import ai_engine.services.eval_service as evaluation
        for function_name in ('_call_gemini_eval_json', '_call_anthropic_eval_json'):
            original = getattr(evaluation, function_name)
            def traced(*args, _fn=original, _name=function_name, **kwargs):
                try:
                    result = _fn(*args, **kwargs)
                    print(_name, 'OK', flush=True)
                    if '--debug-feedback' in sys.argv:
                        import json
                        print(json.dumps(result, ensure_ascii=True)[:16000], flush=True)
                    return result
                except Exception as exc:
                    print(_name, type(exc).__name__,
                          getattr(exc, 'status_code', None) or getattr(exc, 'code', None), flush=True)
                    raise
            setattr(evaluation, function_name, traced)
        if '--written' in sys.argv:
            probe('French written coaching (real provider)', lambda: evaluation.evaluate_ee(
                'Je propose une bibliothèque dans notre quartier. Les habitants pourront y lire et étudier ensemble. '
                'Par exemple, les élèves qui ne disposent pas de livres à la maison pourraient y préparer leurs devoirs. '
                'Cependant, il faudrait prévoir un budget pour les locaux et les livres. Nous pourrions organiser une collecte.',
                'Proposez une amélioration à votre association de quartier.',
                'Présentez une proposition, un avantage et une difficulté.', 'B2', 'fr', require_ai=True,
            ).get('coaching'))
        else:
            probe('French oral evaluation (real provider)', lambda: evaluation.evaluate_eo(
                'Je propose une bibliotheque. Les habitants pourront y lire et etudier ensemble.',
                'Proposer un service local', 'Expliquez votre proposition.', 'B1', [], 'fr', require_ai=True,
            ).get('feedback'))
        sys.exit(0)

    if '--chat' in sys.argv:
        from django.test import override_settings
        from ai_engine.services import llm_service
        def report_failure(provider, exc):
            print(provider, type(exc).__name__,
                  getattr(exc, 'status_code', None) or getattr(exc, 'code', None), flush=True)
        llm_service.failed = report_failure
        with override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}):
            probe('Shared Canada chat service (real provider)', lambda: llm_service.call_llm(
                'Tu es un coach de français.', 'Propose un exercice de français en une phrase.', max_tokens=1024))
        sys.exit(0)

    from openai import OpenAI
    from google import genai
    from google.genai import types

    key = getattr(settings, 'OPENAI_API_KEY', '')
    if key:
        client = OpenAI(api_key=key, timeout=15, max_retries=0)
        probe('OpenAI configured chat model', lambda: client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[{'role': 'user', 'content': 'Reply only OK.'}], max_tokens=8,
        ).choices[0].message.content)
    else:
        print('OpenAI NOT_CONFIGURED', flush=True)

    key = getattr(settings, 'GEMINI_SEARCH_API_KEY', '') or getattr(settings, 'GOOGLE_API_KEY', '')
    if key:
        client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=15000))
        for model in ('gemini-flash-latest', 'gemini-3.6-flash'):
            probe('Gemini ' + model, lambda: client.models.generate_content(
                model=model, contents='Reply only OK.',
                config=types.GenerateContentConfig(max_output_tokens=1024),
            ).text)
    else:
        print('Gemini Studio NOT_CONFIGURED', flush=True)

    from ai_engine.services.eval_service import evaluate_ee, evaluate_eo
    probe('French written evaluation (real provider)', lambda: evaluate_ee(
        'Je propose de planter des arbres dans notre quartier pour offrir de l\u2019ombre aux habitants.',
        'Proposer une amelioration du quartier', 'Expliquez votre proposition.', 'B1', 'fr',
        require_ai=True,
    ).get('feedback'))
    probe('French oral evaluation (sample transcript, real provider)', lambda: evaluate_eo(
        'Je propose une bibliotheque. Les habitants pourront y lire et etudier ensemble.',
        'Proposer un service local', 'Expliquez votre proposition.', 'B1', [], 'fr',
        require_ai=True,
    ).get('feedback'))
