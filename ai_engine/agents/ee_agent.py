import json
import re
from json import JSONDecodeError

from ai_engine.prompts.ee_prompt import EE_SYSTEM_PROMPT
from ai_engine.services.llm_service import call_llm
from ai_engine.validators.ee_validator import validate_ee_json


def _extract_json_text(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty LLM response.")

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")
    return text[start:end + 1].strip()


def generate_ee_content(language: str, level: str, max_retries: int = 2) -> dict:
    lang = (language or "").strip().lower()
    lvl = (level or "").strip().upper()

    if not lang:
        raise ValueError("language is required.")
    if not lvl:
        raise ValueError("level is required.")

    last_error = None
    for _ in range(max_retries + 1):
        raw = call_llm(
            system_prompt=EE_SYSTEM_PROMPT,
            user_prompt=(
                f"Génère une activité EE niveau {lvl} en {lang}. "
                "Réponds UNIQUEMENT en JSON valide avec: topic, instructions, min_words, sample_answer."
            ),
        )
        try:
            data = json.loads(_extract_json_text(raw))
            if not isinstance(data, dict):
                raise ValueError("LLM JSON root must be an object.")
            validate_ee_json(data)
            return data
        except (JSONDecodeError, ValueError) as e:
            last_error = e

    raise RuntimeError(f"Failed to generate valid EE content: {last_error}")