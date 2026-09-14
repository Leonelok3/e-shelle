"""Short provider cooldowns; never treat an API key as a credit balance."""
import os
from django.conf import settings
from django.core.cache import cache


def offline_mode():
    return str(getattr(settings, 'AI_CONTENT_MODE', os.getenv('AI_CONTENT_MODE', 'auto'))).lower() == 'offline'


def available(provider):
    if offline_mode():
        return False
    try:
        return not cache.get('content-ai-cooldown:' + provider)
    except Exception:
        return True


def failed(provider, error):
    text = str(error).lower()
    status = getattr(error, 'status_code', None) or getattr(error, 'code', None)
    permanent = status in (401, 402, 403, 429) or any(word in text for word in (
        'insufficient_quota', 'resource_exhausted', 'billing', 'quota', 'credit', 'api_key_invalid'))
    try:
        cache.set('content-ai-cooldown:' + provider, True, timeout=300 if permanent else 30)
    except Exception:
        pass


def reset():
    for provider in ('openai', 'gemini_vertex', 'gemini_studio'):
        cache.delete('content-ai-cooldown:' + provider)
