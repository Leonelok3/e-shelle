def validate_ce_json(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("CE payload must be an object.")

    reading_text = data.get("reading_text")
    questions = data.get("questions")

    if not isinstance(reading_text, str) or not reading_text.strip():
        raise ValueError("reading_text is required.")
    if not isinstance(questions, list) or not questions:
        raise ValueError("questions must be a non-empty list.")