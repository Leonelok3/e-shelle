import json
import re

from sqlalchemy.orm import Session

from ..models import Tenant


def onboarding_reply(text: str, language: str = "fr") -> str:
    lower = (text or "").lower()
    if "onboarding" not in lower and "config" not in lower and "setup" not in lower:
        return ""
    if language == "en":
        return (
            "ShellBot setup: send your business name, services with prices, opening hours, "
            "FAQ, Calendly link and human fallback email. Example: Business: ... Services: ..."
        )
    return (
        "Configuration ShellBot: envoyez le nom de l'entreprise, les services avec prix, "
        "horaires, FAQ, lien Calendly et email humain de secours. Exemple: Entreprise: ... Services: ..."
    )


def apply_onboarding_update(db: Session, tenant: Tenant, text: str, language: str = "fr") -> str:
    lower = (text or "").lower()
    if not any(token in lower for token in ["entreprise:", "business:", "services:", "faq:", "calendly:", "email:"]):
        return ""

    values = _parse_key_values(text)
    changed = []

    business_name = values.get("entreprise") or values.get("business")
    if business_name:
        tenant.business_name = business_name[:180]
        changed.append("nom")

    email = values.get("email")
    if email:
        tenant.owner_email = email[:180]
        changed.append("email")

    calendly = values.get("calendly")
    if calendly:
        tenant.calendly_url = calendly[:300]
        changed.append("calendly")

    context = values.get("contexte") or values.get("context")
    if context:
        tenant.business_context = context
        changed.append("contexte")

    services = values.get("services")
    if services:
        tenant.services_json = json.dumps(_parse_services(services), ensure_ascii=True)
        changed.append("services")

    faq = values.get("faq")
    if faq:
        tenant.faq_json = json.dumps(_parse_faq(faq), ensure_ascii=True)
        changed.append("faq")

    if not changed:
        return ""

    db.add(tenant)
    db.commit()
    if language == "en":
        return f"Setup updated: {', '.join(changed)}. You can now test your bot with a customer question."
    return f"Configuration mise a jour: {', '.join(changed)}. Vous pouvez maintenant tester le bot avec une question client."


def _parse_key_values(text: str) -> dict[str, str]:
    result = {}
    pattern = re.compile(r"(?im)^(entreprise|business|services|faq|calendly|email|contexte|context)\s*:\s*(.+)$")
    for match in pattern.finditer(text or ""):
        result[match.group(1).lower()] = match.group(2).strip()
    return result


def _parse_services(value: str) -> list[dict]:
    services = []
    for raw in re.split(r"[;|]", value or ""):
        item = raw.strip()
        if not item:
            continue
        amount_match = re.search(r"(\d+)", item)
        amount = int(amount_match.group(1)) if amount_match else 0
        name = re.sub(r"[-:]*\s*\d+\s*\$?\s*(cad)?", "", item, flags=re.I).strip(" -:")
        services.append({"name": name or item, "base_price": amount, "unit": "service"})
    return services


def _parse_faq(value: str) -> list[dict]:
    items = []
    for raw in re.split(r"[|]", value or ""):
        if "=" not in raw:
            continue
        question, answer = raw.split("=", 1)
        question = question.strip()
        answer = answer.strip()
        if question and answer:
            items.append({"question": question, "answer_fr": answer, "answer_en": answer})
    return items
