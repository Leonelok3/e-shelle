import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _client():
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def call_openai(system_prompt: str, user_prompt: str, *, temperature: float = 0.4, max_tokens: int = 2500) -> str:
    client = _client()
    if not client:
        raise RuntimeError("OPENAI_API_KEY n'est pas configurée.")

    model = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def call_openai_json(system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 3000):
    text = call_openai(
        system_prompt,
        user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_obj = text.find("{")
        start_arr = text.find("[")
        starts = [idx for idx in (start_obj, start_arr) if idx != -1]
        if not starts:
            raise
        start = min(starts)
        end = max(text.rfind("}"), text.rfind("]"))
        if end <= start:
            raise
        return json.loads(text[start:end + 1])
