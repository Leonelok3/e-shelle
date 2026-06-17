import json

from openai import OpenAI

from ..config import get_settings
from ..models import Tenant


def find_faq_answer(tenant: Tenant, text: str, language: str) -> str:
    faqs = json.loads(tenant.faq_json or "[]")
    lower = (text or "").lower()
    best = None
    best_score = 0
    for faq in faqs:
        question = faq.get("question", "").lower()
        tokens = [token for token in question.replace("?", "").split() if len(token) > 3]
        score = sum(1 for token in tokens if token in lower)
        if score > best_score:
            best = faq
            best_score = score
    if best and best_score:
        return best.get("answer_en" if language == "en" else "answer_fr", "") or best.get("answer_fr", "")
    return ""


def generate_ai_reply(tenant: Tenant, history: list[str], user_text: str, language: str) -> str:
    faq = find_faq_answer(tenant, user_text, language)
    if faq:
        return faq

    settings = get_settings()
    fallback = (
        "Merci. Je peux vous aider avec les prix, un devis, un rendez-vous ou transmettre a un humain."
        if language == "fr"
        else "Thanks. I can help with pricing, a quote, an appointment, or transfer you to a human."
    )
    if not settings.openai_api_key:
        return fallback

    client = OpenAI(api_key=settings.openai_api_key)
    system = (
        f"You are ShellBot for {tenant.business_name}. "
        f"Business context: {tenant.business_context}. "
        "Reply briefly, professionally, and never invent firm prices beyond configured quote estimates. "
        "If uncertain, ask one short clarification or suggest human handoff."
    )
    messages = [{"role": "system", "content": system}]
    for item in history[-8:]:
        messages.append({"role": "user", "content": item})
    messages.append({"role": "user", "content": user_text})
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.3,
        max_tokens=220,
    )
    return response.choices[0].message.content.strip()

