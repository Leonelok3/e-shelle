from typing import Callable, Any

from ai_engine.agents.co_agent import generate_co_content
from ai_engine.agents.ce_agent import generate_ce_content
from ai_engine.agents.eo_agent import generate_eo_content
from ai_engine.agents.ee_agent import generate_ee_content

from ai_engine.services.ce_insertion_service import insert_ce_content
from ai_engine.services.eo_insertion_service import insert_eo_content
from ai_engine.services.ee_insertion_service import insert_ee_content
from ai_engine.services.skill_insertion_base import insert_standard_payload
from ai_engine.services.content_normalizer import normalize_agent_payload


def _insert_co_content(payload: dict | str, saver=None):
    return insert_standard_payload(payload=payload, expected_skill="CO", saver=saver)


_GENERATORS: dict[str, Callable[..., dict | str]] = {
    "CO": generate_co_content,
    "CE": generate_ce_content,
    "EO": generate_eo_content,
    "EE": generate_ee_content,
}

_INSERTERS: dict[str, Callable[..., Any]] = {
    "CO": _insert_co_content,
    "CE": insert_ce_content,
    "EO": insert_eo_content,
    "EE": insert_ee_content,
}


def generate_and_insert(skill: str, language: str, level: str, saver=None):
    s = (skill or "").strip().upper()
    lang = (language or "").strip().lower()
    lvl = (level or "").strip().upper()

    if not s or not lang or not lvl:
        raise ValueError("skill, language, and level are required.")

    if s not in _GENERATORS:
        raise ValueError("Unsupported skill. Allowed: CO, CE, EO, EE.")

    raw_payload = _GENERATORS[s](language=lang, level=lvl)
    normalized_payload = normalize_agent_payload(s, lang, lvl, raw_payload)

    return _INSERTERS[s](normalized_payload, saver=saver)