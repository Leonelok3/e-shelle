from .openai_service import ask_openai

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
    prompt = CANADA_EXPERIENCE_PROMPT.format(
        title=experience.title,
        company=experience.company,
        description=experience.description_raw
    )

    response = ask_openai(prompt)
    return response.strip()
