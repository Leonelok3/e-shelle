import json
import re

from ..models import Tenant


def estimate_quote(tenant: Tenant, need: str, language: str = "fr") -> tuple[int, str]:
    services = json.loads(tenant.services_json or "[]")
    text = (need or "").lower()
    selected = []
    total = 0
    for service in services:
        name = service.get("name", "")
        base = int(service.get("base_price") or 0)
        words = [w for w in re.split(r"\W+", name.lower()) if len(w) > 3]
        if any(word in text for word in words):
            selected.append((name, base))
            total += base

    if not selected and services:
        base = int(services[0].get("base_price") or 0)
        selected = [(services[0].get("name", "Service"), base)]
        total = base

    if language == "en":
        lines = [
            f"Quote for {tenant.business_name}",
            "",
            f"Request: {need}",
            "Items:",
            *[f"- {name}: ${amount} CAD" for name, amount in selected],
            "",
            f"Estimated total: ${total} CAD",
            "This quote is indicative. A team member can confirm details and timing.",
        ]
    else:
        lines = [
            f"Devis pour {tenant.business_name}",
            "",
            f"Besoin: {need}",
            "Elements:",
            *[f"- {name}: {amount}$ CAD" for name, amount in selected],
            "",
            f"Total estime: {total}$ CAD",
            "Ce devis est indicatif. Un humain peut confirmer les details et les delais.",
        ]
    return total, "\n".join(lines)

