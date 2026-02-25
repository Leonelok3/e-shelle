import json
import logging
import re
from json import JSONDecodeError

from ai_engine.prompts.co_prompt import CO_SYSTEM_PROMPT
from ai_engine.services.llm_service import call_llm
from ai_engine.validators.co_validator import validate_co_json

logger = logging.getLogger(__name__)


def _extract_json_text(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty LLM response.")

    # Supporte réponse markdown ```json ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # Sinon tente bloc JSON brut
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")
    return text[start : end + 1].strip()


def _parse_llm_json(raw: str) -> dict:
    json_text = _extract_json_text(raw)
    try:
        data = json.loads(json_text)
    except JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e.msg}") from e

    if not isinstance(data, dict):
        raise ValueError("LLM JSON root must be an object.")
    return data


def generate_co_content(language: str, level: str, max_retries: int = 2) -> dict:
    lang = (language or "").strip().lower()
    lvl = (level or "").strip().upper()
    if not lang:
        raise ValueError("language is required.")
    if not lvl:
        raise ValueError("level is required.")

    last_error = None
    for attempt in range(max_retries + 1):
        raw = call_llm(
            system_prompt=CO_SYSTEM_PROMPT,
            user_prompt=(
                f"Génère une leçon CO niveau {lvl} en {lang}. "
                "Réponds UNIQUEMENT en JSON valide avec les clés: "
                "audio_script (string), questions (array)."
            ),
        )

        try:
            data = _parse_llm_json(raw)
            validate_co_json(data)
            return data
        except Exception as e:
            last_error = e
            logger.warning("CO agent attempt %s/%s failed: %s", attempt + 1, max_retries + 1, e)

    raise RuntimeError(f"Failed to generate valid CO content after {max_retries + 1} attempts: {last_error}")