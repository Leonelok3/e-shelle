def validate_eo_json(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("EO payload must be an object.")

    topic = data.get("topic")
    instructions = data.get("instructions")
    expected_points = data.get("expected_points")

    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic is required.")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("instructions is required.")
    if not isinstance(expected_points, list) or not expected_points:
        raise ValueError("expected_points must be a non-empty list.")