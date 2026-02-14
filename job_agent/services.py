import re
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMessage

# PDF extraction
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


# =========================================================
# MATCHING
# =========================================================
@dataclass
class MatchResult:
    score: int
    summary: str


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    text = text.lower()
    text = re.sub(r"[^a-z0-9àâäçéèêëîïôöùûüœæ\s\-]", " ", text)
    parts = re.split(r"[\s\-]+", text)
    return {p for p in parts if len(p) >= 3}


def heuristic_match(cv_text: str, offer_text: str, keywords: str = "") -> MatchResult:
    cv_tokens = _tokenize(cv_text)
    offer_tokens = _tokenize(offer_text)
    kw_tokens = _tokenize(keywords)

    if not offer_tokens:
        return MatchResult(
            score=0,
            summary="Aucune description fournie : colle la description de l'offre pour un meilleur score.",
        )

    overlap = cv_tokens.intersection(offer_tokens)
    overlap_kw = kw_tokens.intersection(offer_tokens)

    base = min(70, int(len(overlap) * 2.5))
    boost = min(30, int(len(overlap_kw) * 6))
    score = max(0, min(100, base + boost))

    summary = (
        f"Score calculé sur mots en commun CV↔offre ({len(overlap)}), "
        f"mots-clés recherchés présents ({len(overlap_kw)}). "
        f"Conseil: ajoute des mots-clés précis dans ta recherche."
    )

    return MatchResult(score=score, summary=summary)


# =========================================================
# GENERATION (lettre + réponses + email)
# =========================================================
def generate_application_texts(
    *,
    offer_title: str,
    company: str,
    location: str,
    offer_text: str,
    cv_text: str,
    base_letter: str,
    language: str = "fr",
) -> dict:

    lang = (language or "fr").lower()
    offer_title = offer_title or "Poste"
    company = company or ""
    location = location or ""

    if lang.startswith("en"):
        email_subject = f"Application — {offer_title}{(' — ' + company) if company else ''}"
        email_body = (
            f"Hello {company or 'Hiring Team'},\n\n"
            f"I’m applying for the {offer_title} position"
            f"{(' in ' + location) if location else ''}.\n\n"
            f"Please find attached my resume and cover letter.\n"
            f"I’m available for an interview or assessment.\n\n"
            f"Best regards,\n"
        )
    else:
        email_subject = f"Candidature — {offer_title}{(' — ' + company) if company else ''}"
        email_body = (
            f"Bonjour {company or 'Madame, Monsieur'},\n\n"
            f"Je vous soumets ma candidature au poste de {offer_title}"
            f"{(' à ' + location) if location else ''}.\n\n"
            f"Veuillez trouver ci-joint mon CV et ma lettre de motivation.\n"
            f"Je reste disponible pour un échange (entretien / test).\n\n"
            f"Cordialement,\n"
        )

    if lang.startswith("en"):
        letter = (
            f"Subject: Application for {offer_title}\n\n"
            f"Hello {company or 'Hiring Team'},\n\n"
            f"I’m applying for the {offer_title} position.\n\n"
            f"{base_letter.strip() if base_letter else 'I would be happy to discuss how my experience can help your team.'}\n\n"
            f"Best regards,\n"
        )
        answers = {
            "Availability": "Available immediately / within 2 weeks.",
            "Salary expectations": "Open to discussion.",
            "Motivation": f"Strong interest in {offer_title}.",
        }
    else:
        letter = (
            f"Objet : Candidature au poste de {offer_title}\n\n"
            f"Bonjour {company or 'Madame, Monsieur'},\n\n"
            f"Je vous soumets ma candidature pour le poste de {offer_title}.\n\n"
            f"{base_letter.strip() if base_letter else 'Je serais ravi(e) d’échanger avec vous afin de détailler ma motivation.'}\n\n"
            f"Cordialement,\n"
        )
        answers = {
            "Disponibilité": "Disponible immédiatement / sous 2 semaines.",
            "Prétentions salariales": "À discuter.",
            "Motivation": f"Très motivé(e) par le poste de {offer_title}.",
        }

    return {
        "letter": letter.strip(),
        "answers": answers,
        "email_subject": email_subject.strip(),
        "email_body": email_body.strip(),
    }


# =========================================================
# TEMPLATE SAFE
# =========================================================
def render_text_template(template_text: str, **kwargs) -> str:
    template_text = template_text or ""
    try:
        return template_text.format(**{k: (v or "") for k, v in kwargs.items()}).strip()
    except Exception:
        return template_text.strip()


# =========================================================
# SMTP SAFE
# =========================================================
def send_followup_email(*, to_email: str, subject: str, body: str) -> None:
    subject = (subject or "").strip()
    body = (body or "").strip()
    to_email = (to_email or "").strip()

    if not subject or not body or not to_email:
        raise ValueError("Email invalide.")

    sender = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

    msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=sender,
        to=[to_email],
    )
    msg.send(fail_silently=False)


# =========================================================
# EXTRACTION PDF
# =========================================================
def extract_text_from_pdf_file(file_obj) -> str:
    if PdfReader is None:
        return ""

    try:
        if hasattr(file_obj, "open"):
            file_obj.open("rb")
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        reader = PdfReader(file_obj)
        texts = []

        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                texts.append(t)

        raw = "\n".join(texts).strip()
        raw = raw.replace("\x00", " ")
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)

        return raw[:200_000]

    except Exception:
        return ""


def extract_cv_text_from_file(file_obj, filename: Optional[str] = None) -> str:
    name = (filename or getattr(file_obj, "name", "") or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf_file(file_obj)
    return ""
