import logging
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client, get_genai_studio_client
from ai_engine.services.availability import available, failed

logger = logging.getLogger(__name__)


def call_llm(system_prompt: str, user_prompt: str, model: str = "gemini-3.6-flash", *, fallback=None, max_tokens=2500, usage=None) -> str:
    """Use paid providers when available, otherwise an explicit task-specific fallback.

    Fallbacks are deliberately supplied by callers: no invented generic output
    is returned for arbitrary requests, source extraction or scoring.
    """
    if available('openai'):
        try:
            from ai_engine.services.openai_adapter import call_openai
            options = {'usage': usage} if usage is not None else {}
            result = call_openai(system_prompt, user_prompt, max_tokens=max_tokens, **options)
            if result and result.strip():
                return result.strip()
            raise ValueError('Empty AI response')
        except Exception as error:
            failed('openai', error)
            logger.warning('Content provider openai unavailable (%s)', type(error).__name__)
    for provider, factory in [('gemini_vertex', get_vertex_client), ('gemini_studio', get_genai_studio_client)]:
        if not available(provider):
            continue
        try:
            client, error = factory()
            if error or not client:
                raise RuntimeError('AI client unavailable')
            response = client.models.generate_content(model=model, contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.7, max_output_tokens=max_tokens))
            if response.text and response.text.strip():
                if usage is not None:
                    metadata = response.usage_metadata
                    usage.update(model=getattr(response, 'model_version', None) or model,
                                 input_tokens=(metadata.prompt_token_count or 0) if metadata else 0,
                                 output_tokens=(metadata.candidates_token_count or 0) if metadata else 0)
                return response.text.strip()
            raise ValueError('Empty AI response')
        except Exception as error:
            failed(provider, error)
            logger.warning('Content provider %s unavailable (%s)', provider, type(error).__name__)
    if fallback is not None:
        result = fallback() if callable(fallback) else fallback
        if isinstance(result, str) and result.strip():
            logger.info('Content generated with local fallback')
            return result
    raise RuntimeError('Les fournisseurs IA sont temporairement indisponibles.')


def stream_llm(system_prompt, user_prompt, *, usage, max_tokens=2048):
    """Stream text, failing over only before any text has reached the caller."""
    from django.conf import settings
    from ai_engine.services.openai_adapter import _client

    providers = [('openai', _client), ('gemini_vertex', get_vertex_client),
                 ('gemini_studio', get_genai_studio_client)]
    for provider, factory in providers:
        if not available(provider):
            continue
        emitted = False
        stream = None
        try:
            if provider == 'openai':
                client = factory()
                if not client:
                    continue
                model = getattr(settings, 'OPENAI_CHAT_MODEL', 'gpt-4o')
                stream = client.chat.completions.create(
                    model=model, max_tokens=max_tokens, stream=True,
                    stream_options={'include_usage': True},
                    messages=[{'role': 'system', 'content': system_prompt},
                              {'role': 'user', 'content': user_prompt}],
                )
                usage.update(model=model, input_tokens=0, output_tokens=0)
                for chunk in stream:
                    if chunk.model:
                        usage['model'] = chunk.model
                    if chunk.usage:
                        usage.update(input_tokens=chunk.usage.prompt_tokens,
                                     output_tokens=chunk.usage.completion_tokens)
                    text = chunk.choices[0].delta.content if chunk.choices else None
                    if text:
                        emitted = True
                        yield text
            else:
                client, error = factory()
                if error or not client:
                    continue
                model = 'gemini-3.6-flash'
                stream = client.models.generate_content_stream(
                    model=model, contents=user_prompt,
                    config=types.GenerateContentConfig(system_instruction=system_prompt,
                        max_output_tokens=max_tokens, http_options=types.HttpOptions(timeout=30000)),
                )
                usage.update(model=model, input_tokens=0, output_tokens=0)
                for chunk in stream:
                    if chunk.usage_metadata:
                        usage.update(input_tokens=chunk.usage_metadata.prompt_token_count or 0,
                                     output_tokens=chunk.usage_metadata.candidates_token_count or 0)
                    if getattr(chunk, 'model_version', None):
                        usage['model'] = chunk.model_version
                    if chunk.text:
                        emitted = True
                        yield chunk.text
            if emitted:
                return
            raise ValueError('Empty AI response')
        except Exception as error:
            failed(provider, error)
            logger.warning('Streaming provider %s unavailable (%s)', provider, type(error).__name__)
            if emitted:
                raise RuntimeError('La génération a été interrompue. Veuillez réessayer.') from error
        finally:
            if stream is not None and hasattr(stream, 'close'):
                stream.close()
    raise RuntimeError('Les fournisseurs IA sont temporairement indisponibles.')
