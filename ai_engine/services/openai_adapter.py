import json
import logging
import re
import urllib.parse
from html import unescape

from django.conf import settings
import requests

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


def search_duckduckgo(query: str, max_results: int = 10) -> str:
    """
    Recherche web légère sans API payante, utilisée quand Gemini Search Grounding
    n'est pas disponible.
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=12)
    response.raise_for_status()

    def clean_html(value: str) -> str:
        return unescape(re.sub(r"<.*?>", "", value or "")).strip()

    def clean_link(value: str) -> str:
        value = unescape(value or "").strip()
        parsed = urllib.parse.urlparse(value)
        query_params = urllib.parse.parse_qs(parsed.query)
        if "uddg" in query_params:
            return query_params["uddg"][0]
        return value

    blocks = re.findall(
        r'<div class="result.*?">(.*?)</div>\s*</div>\s*</div>',
        response.text,
        re.DOTALL,
    )
    results = []
    for block in blocks:
        link_match = re.search(r'class="result__a"[^>]+href="(.*?)"[^>]*>(.*?)</a>', block, re.DOTALL)
        if not link_match:
            continue
        snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
        title = clean_html(link_match.group(2))
        link = clean_link(link_match.group(1))
        snippet = clean_html(snippet_match.group(1) if snippet_match else "")
        if title and link:
            results.append(f"Titre: {title}\nURL: {link}\nExtrait: {snippet}")
        if len(results) >= max_results:
            break

    if not results:
        logger.warning("DuckDuckGo n'a retourné aucun résultat parsable pour: %s", query)
    return "\n\n".join(results)
