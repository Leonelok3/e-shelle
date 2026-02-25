import json
from typing import Callable, Any


def _to_dict(payload: dict | str) -> dict:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e.msg}") from e
        if not isinstance(data, dict):
            raise ValueError("Payload root must be a JSON object.")
        return data
    raise ValueError("Payload must be dict or JSON string.")


def validate_standard_payload(data: dict, expected_skill: str) -> None:
    required = ["title", "skill", "level", "language", "content", "questions"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Missing keys: {missing}")

    if data["skill"] != expected_skill:
        raise ValueError(f"Expected skill '{expected_skill}', got '{data['skill']}'.")

    if not isinstance(data["title"], str) or not data["title"].strip():
        raise ValueError("title is required.")
    if not isinstance(data["level"], str) or not data["level"].strip():
        raise ValueError("level is required.")
    if not isinstance(data["language"], str) or not data["language"].strip():
        raise ValueError("language is required.")
    if not isinstance(data["content"], dict) or not data["content"]:
        raise ValueError("content must be a non-empty object.")
    if not isinstance(data["questions"], list):
        raise ValueError("questions must be a list.")


def insert_standard_payload(
    payload: dict | str,
    expected_skill: str,
    saver: Callable[[dict], Any] | None = None,
):
    data = _to_dict(payload)
    validate_standard_payload(data, expected_skill)

    # Si tu veux persister en DB, passe une fonction saver(data)
    if saver is not None:
        return saver(data)

    # Mode safe par défaut (ne casse rien)
    return {"inserted": False, "skill": expected_skill, "payload": data}