def validate_co_json(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("CO payload must be an object.")
    if not isinstance(data.get("audio_script"), str) or not data["audio_script"].strip():
        raise ValueError("audio_script is required.")
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("questions must be a non-empty list.")