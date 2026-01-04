from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def translate_cv_text(text, source_lang, target_lang, job_title):
    """
    Traduction professionnelle CV Canada (ATS-safe)
    """

    prompt = f"""
You are a professional Canadian resume translator.

Task:
Translate the following resume content from {source_lang} to {target_lang}.

Rules:
- Use Canadian resume standards
- ATS compatible wording
- Keep professional tone
- No literal translation
- Adapt terminology to the job role
- Do NOT add information
- Do NOT remove information
- No emojis

Job title:
{job_title}

Text:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600
    )

    return response.choices[0].message.content.strip()
