def normalize_agent_payload(skill: str, language: str, level: str, raw: dict) -> dict:
    s = (skill or "").strip().upper()
    lang = (language or "").strip().lower()
    lvl = (level or "").strip().upper()

    if not isinstance(raw, dict):
        raise ValueError("Agent payload must be a dict.")

    if s == "CO":
        content = {"audio_script": raw.get("audio_script", "")}
        questions = raw.get("questions", [])
        title = f"CO {lvl} - Listening practice"
    elif s == "CE":
        content = {"reading_text": raw.get("reading_text", "")}
        questions = raw.get("questions", [])
        title = f"CE {lvl} - Reading practice"
    elif s == "EO":
        content = {
            "topic": raw.get("topic", ""),
            "instructions": raw.get("instructions", ""),
            "expected_points": raw.get("expected_points", []),
        }
        questions = []
        title = f"EO {lvl} - Speaking practice"
    elif s == "EE":
        content = {
            "topic": raw.get("topic", ""),
            "instructions": raw.get("instructions", ""),
            "min_words": raw.get("min_words", 0),
            "sample_answer": raw.get("sample_answer", ""),
        }
        questions = []
        title = f"EE {lvl} - Writing practice"
    else:
        raise ValueError("Unsupported skill. Allowed: CO, CE, EO, EE.")

    return {
        "title": title,
        "skill": s,
        "level": lvl,
        "language": lang,
        "content": content,
        "questions": questions,
    }