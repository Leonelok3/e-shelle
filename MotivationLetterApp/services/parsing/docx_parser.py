from docx import Document
from . import normalize_cv_text  # ← import nécessaire

def parse_docx(path: str) -> dict:
    try:
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)
        return normalize_cv_text(text)
    except Exception as e:
        return {"error": f"DOCX parse failed: {e}"}
