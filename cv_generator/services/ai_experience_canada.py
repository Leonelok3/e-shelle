import logging
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)

CANADA_EXPERIENCE_PROMPT = """
Tu es un recruteur canadien expert ATS.

Réécris cette expérience professionnelle pour un CV canadien :
- phrases courtes
- verbes d’action
- mots-clés métiers
- format bullet points
- orienté résultats
- compatible ATS (Canada)

Poste : {title}
Entreprise : {company}
Description brute :
{description}

Retourne uniquement le texte final, sans titre.
"""


def optimize_experience_for_canada(experience):
    raw = (experience.description_raw or experience.description or "").strip()
    title = (experience.title or "").strip()
    company = (experience.company or "").strip()

    if not raw:
        return raw

    try:
        service = OpenAIService()
        result = service.enhance_experience_description(
            raw=raw,
            job_title=title,
            industry=company,
        )
        return result.strip()
    except Exception as e:
        logger.warning("optimize_experience_for_canada failed: %s", e)
        return raw
