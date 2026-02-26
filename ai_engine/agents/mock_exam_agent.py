import json
import logging
import re
from json import JSONDecodeError

from ai_engine.services.llm_service import call_llm

logger = logging.getLogger(__name__)

SECTION_PROMPTS = {
    "co": "ai_engine.prompts.mock_exam_prompt.MOCK_EXAM_CO_PROMPT",
    "ce": "ai_engine.prompts.mock_exam_prompt.MOCK_EXAM_CE_PROMPT",
    "eo": "ai_engine.prompts.mock_exam_prompt.MOCK_EXAM_EO_PROMPT",
    "ee": "ai_engine.prompts.mock_exam_prompt.MOCK_EXAM_EE_PROMPT",
}


def _get_prompt(section: str) -> str:
    from ai_engine.prompts.mock_exam_prompt import (
        MOCK_EXAM_CE_PROMPT,
        MOCK_EXAM_CO_PROMPT,
        MOCK_EXAM_EE_PROMPT,
        MOCK_EXAM_EO_PROMPT,
    )
    return {
        "co": MOCK_EXAM_CO_PROMPT,
        "ce": MOCK_EXAM_CE_PROMPT,
        "eo": MOCK_EXAM_EO_PROMPT,
        "ee": MOCK_EXAM_EE_PROMPT,
    }[section]


def _extract_json(raw: str) -> str:
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


def _validate_questions(questions: list, section: str) -> list:
    validated = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        stem = q.get("stem", "").strip()
        if not stem:
            continue
        choices = q.get("choices", [])
        if not isinstance(choices, list) or len(choices) < 2:
            continue
        difficulty = q.get("difficulty", "medium").lower()
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"
        validated.append({
            "stem": stem,
            "difficulty": difficulty,
            "passage": q.get("passage", ""),
            "choices": choices,
            "explanation": q.get("explanation", ""),
        })
    return validated


def generate_mock_exam_questions(
    section: str,
    level: str,
    language: str = "fr",
    max_retries: int = 2,
) -> dict:
    """
    Génère 5 questions QCM type TEF pour une section donnée.

    Returns:
        {
            "passage": "...",  # CO et CE uniquement
            "questions": [
                {
                    "stem": "...",
                    "difficulty": "medium",
                    "choices": [{"text": "...", "is_correct": bool}, ...],
                    "explanation": "..."
                }
            ]
        }
    """
    sec = (section or "").strip().lower()
    lvl = (level or "").strip().upper()
    lang = (language or "fr").strip().lower()

    if sec not in ("co", "ce", "eo", "ee"):
        raise ValueError(f"Section invalide: '{section}'. Choisir parmi: co, ce, eo, ee")
    if not lvl:
        raise ValueError("level est requis.")

    system_prompt = _get_prompt(sec)
    user_prompt = (
        f"Génère 5 questions type TEF Canada, section {sec.upper()}, "
        f"niveau {lvl}, en {lang}. "
        f"Difficulté adaptée au niveau {lvl}. "
        f"Réponds UNIQUEMENT en JSON valide selon le format demandé."
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
            data = json.loads(_extract_json(raw))

            if not isinstance(data, dict):
                raise ValueError("LLM JSON root must be an object.")

            questions = data.get("questions", [])
            if not isinstance(questions, list) or not questions:
                raise ValueError("No questions in response.")

            validated = _validate_questions(questions, sec)
            if not validated:
                raise ValueError("No valid questions after validation.")

            return {
                "passage": data.get("passage", ""),
                "questions": validated,
            }

        except (JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(
                "MockExam agent [%s] attempt %s/%s failed: %s",
                sec.upper(), attempt + 1, max_retries + 1, e
            )

    raise RuntimeError(
        f"Failed to generate mock exam questions [{sec.upper()}] "
        f"after {max_retries + 1} attempts: {last_error}"
    )
