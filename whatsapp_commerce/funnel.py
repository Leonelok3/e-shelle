"""Qualification and response sequencing for the WhatsApp sales assistant."""

import re

from .brain import generate_sales_decision

_BUDGET = re.compile(r"\b(\d[\d\s.,]{2,})\s*(?:fcfa|xaf|francs?)?\b", re.I)
_URGENCY = re.compile(r"\b(urgent|aujourd'hui|maintenant|cette semaine|demain|plus tard)\b", re.I)


def _catalog_intro(connection):
	business = connection.business
	items = list(
		connection.agent_catalog_items.filter(
			business=business,
			is_active=True,
		).order_by("order", "-created_at")[:2]
	)
	if not items:
		items = list(business.catalog_items.filter(is_active=True).order_by("order", "-created_at")[:2])
	if not items:
		return ""
	lines = ["Voici deux options de notre catalogue E-Shelle :"]
	for item in items:
		price = item.price_label or "prix à confirmer"
		lines.append(f"• {item.title} — {price}")
	return "\n".join(lines)


def _update_qualification(contact, message, decision):
	fields = contact.custom_fields if isinstance(contact.custom_fields, dict) else {}
	qualification = fields.get("qualification", {})
	if not isinstance(qualification, dict):
		qualification = {}
	qualification.setdefault("need", (message or "")[:500])
	budget_match = _BUDGET.search(message or "")
	if budget_match:
		qualification["budget"] = budget_match.group(1).strip()
	urgency_match = _URGENCY.search(message or "")
	if urgency_match:
		qualification["urgency"] = urgency_match.group(1).lower()
	qualification.setdefault("city", "")
	fields["qualification"] = qualification
	contact.custom_fields = fields
	contact.save(update_fields=["custom_fields", "last_activity_at"])
	return qualification


def build_funnel_reply(connection, contact, inbound_message):
	"""Create an initial catalog introduction, then qualify before proposing a close."""
	decision = generate_sales_decision(connection, contact, inbound_message.body)
	if decision.get("pending_action", {}).get("status") == "awaiting_confirmation":
		return decision
	qualification = _update_qualification(contact, inbound_message.body, decision)
	inbound_count = contact.messages.filter(direction="inbound").count()
	if inbound_count == 1:
		intro = _catalog_intro(connection)
		question = "Qu’est-ce que tu recherches, quel budget as-tu prévu et pour quand en as-tu besoin ?"
		reply = "\n\n".join(part for part in (intro, question) if part)
		return {**decision, "reponse": reply or decision["reponse"], "action_next": "qualifier"}
	missing = [
		key for key in ("budget", "urgency")
		if not qualification.get(key)
	]
	if missing:
		question = (
			"Pour te proposer la bonne option, quel budget souhaites-tu prévoir ?"
			if "budget" in missing
			else "Tu en as besoin pour quand : aujourd’hui, cette semaine ou plus tard ?"
		)
		return {**decision, "reponse": question, "action_next": "qualifier"}
	return decision
