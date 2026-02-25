from ai_engine.agents.co_agent import generate_co_content
from ai_engine.agents.ce_agent import generate_ce_content
from ai_engine.agents.eo_agent import generate_eo_content
from ai_engine.agents.ee_agent import generate_ee_content

from ai_engine.services.ce_insertion_service import insert_ce_content
from ai_engine.services.eo_insertion_service import insert_eo_content
from ai_engine.services.ee_insertion_service import insert_ee_content
from ai_engine.services.skill_insertion_base import insert_standard_payload


def _insert_co_content(payload: dict | str, saver=None):
    return insert_standard_payload(payload=payload, expected_skill="CO", saver=saver)


def generate_and_insert(skill: str, language: str, level: str, saver=None):
    s = (skill or "").strip().upper()

    if s == "CO":
        payload = generate_co_content(language=language, level=level)
        return _insert_co_content(payload, saver=saver)

    if s == "CE":
        payload = generate_ce_content(language=language, level=level)
        return insert_ce_content(payload, saver=saver)

    if s == "EO":
        payload = generate_eo_content(language=language, level=level)
        return insert_eo_content(payload, saver=saver)

    if s == "EE":
        payload = generate_ee_content(language=language, level=level)
        return insert_ee_content(payload, saver=saver)

    raise ValueError("Unsupported skill. Allowed: CO, CE, EO, EE.")