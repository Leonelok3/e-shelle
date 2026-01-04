import docx2txt
import pdfplumber

def extract_text_from_cv(path):
    if path.endswith(".pdf"):
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    if path.endswith(".docx"):
        return docx2txt.process(path)

    return ""
