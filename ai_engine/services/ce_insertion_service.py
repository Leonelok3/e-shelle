from ai_engine.services.skill_insertion_base import insert_standard_payload


def insert_ce_content(payload: dict | str, saver=None):
    return insert_standard_payload(payload=payload, expected_skill="CE", saver=saver)