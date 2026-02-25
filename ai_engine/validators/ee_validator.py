def validate_ee_json(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("EE payload must be an object.")

    topic = data.get("topic")
    instructions = data.get("instructions")
    min_words = data.get("min_words")
    sample_answer = data.get("sample_answer")

    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic is required.")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("instructions is required.")
    if not isinstance(min_words, int) or min_words <= 0:
        raise ValueError("min_words must be a positive integer.")
    if not isinstance(sample_answer, str) or not sample_answer.strip():
        raise ValueError("sample_answer is required.")