from pdfminer.high_level import extract_text
from . import normalize_cv_text  # ← import nécessaire

def parse_pdf(path: str) -> dict:
    try:
        text = extract_text(path)
        return normalize_cv_text(text)
    except Exception as e:
        return {"error": f"PDF parse failed: {e}"}
