from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def improve_experience_description(
    title,
    company,
    raw_text,
    language="fr"
):
    if not raw_text:
        return ""

    prompt = f"""
Tu es un expert en recrutement au Canada.

Améliore la description suivante pour un CV canadien :
- style professionnel
- compatible ATS
- phrases courtes
- verbes d’action
- résultats mesurables si possible
- pas d’informations inventées

Poste : {title}
Entreprise : {company}

Texte original :
{raw_text}

Rends la réponse sous forme de liste à puces.
"""

    if language == "en":
        prompt = prompt.replace("Tu es un expert en recrutement au Canada.", 
                                 "You are a Canadian recruitment expert.")
        prompt = prompt.replace("Améliore la description suivante", 
                                 "Improve the following job description")
        prompt = prompt.replace("Rends la réponse sous forme de liste à puces.",
                                 "Return the result as bullet points.")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()
