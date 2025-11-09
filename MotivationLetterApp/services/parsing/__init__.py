import re

def normalize_cv_text(text: str) -> dict:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return {
        "raw_text": text,
        "profile": lines[:3] if len(lines) > 3 else lines,
        "experiences": [l for l in lines if "experience" in l.lower()],
        "skills": [l for l in lines if "competence" in l.lower() or "skill" in l.lower()],
        "education": [l for l in lines if "dipl" in l.lower() or "education" in l.lower()],
        "achievements": [l for l in lines if "réalisation" in l.lower() or "achievement" in l.lower()],
    }
