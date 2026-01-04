from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_professional_summary(cv):
    """
    Génère un résumé professionnel ATS Canada
    """

    experiences = cv.experiences.all()
    skills = cv.skills.all()

    exp_text = "\n".join([
        f"- {e.title} at {e.company}" for e in experiences
    ])

    skill_text = ", ".join([s.name for s in skills])

    prompt = f"""
You are a Canadian recruitment expert and ATS specialist.

Generate a professional resume summary for Canada.

Rules:
- 3 to 4 lines maximum
- No first person ("I")
- Professional, clear, factual
- Optimized for ATS
- No emojis
- No buzzwords without value

Profile:
Job title: {cv.profession}
Target country: Canada
Experience:
{exp_text}

Skills:
{skill_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=120
    )

    return response.choices[0].message.content.strip()
