import json
import os


def _mock_response(user_prompt: str) -> str:
    p = (user_prompt or "").upper()

    if " CE " in f" {p} ":
        return json.dumps(
            {
                "reading_text": "Bonjour, je m'appelle Lina. J'habite à Lyon.",
                "questions": [
                    {
                        "question": "Où habite Lina ?",
                        "choices": ["Paris", "Lyon", "Lille", "Nice"],
                        "correct_answer": "B",
                    }
                ],
            },
            ensure_ascii=False,
        )

    if " EO " in f" {p} ":
        return json.dumps(
            {
                "topic": "Se présenter",
                "instructions": "Parlez de vous pendant 2 minutes.",
                "expected_points": ["identité", "profession", "objectifs"],
            },
            ensure_ascii=False,
        )

    if " EE " in f" {p} ":
        return json.dumps(
            {
                "topic": "Mon projet professionnel",
                "instructions": "Rédigez un texte structuré.",
                "min_words": 120,
                "sample_answer": "Je souhaite évoluer dans un environnement international.",
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "audio_script": "Bonjour. Aujourd'hui, nous parlons du travail.",
            "questions": [
                {
                    "question": "Sujet principal ?",
                    "choices": ["Sport", "Travail", "Cuisine", "Voyage"],
                    "correct_answer": "B",
                }
            ],
        },
        ensure_ascii=False,
    )


def call_llm(system_prompt: str, user_prompt: str) -> str:
    if os.getenv("LLM_MOCK_MODE", "1").strip() == "1":
        return _mock_response(user_prompt)
    raise RuntimeError("LLM backend not configured yet.")