import logging
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client, get_genai_studio_client
from ai_engine.services.availability import available, failed

logger = logging.getLogger(__name__)


def call_llm(system_prompt: str, user_prompt: str, model: str = "gemini-3.6-flash", *, fallback=None, max_tokens=2500) -> str:
    """Use paid providers when available, otherwise an explicit task-specific fallback.

    Fallbacks are deliberately supplied by callers: no invented generic output
    is returned for arbitrary requests, source extraction or scoring.
    """
    if available('openai'):
        try:
            from ai_engine.services.openai_adapter import call_openai
            result = call_openai(system_prompt, user_prompt, max_tokens=max_tokens)
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
