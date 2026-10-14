"""Safe adapter from sales intent to E-Shelle commerce actions."""

import logging
import unicodedata
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from business.models import BusinessCatalogItem

from .models import BusinessWhatsAppAudit, BusinessWhatsAppMessage

logger = logging.getLogger(__name__)


def _normalized(value):
	value = unicodedata.normalize("NFKD", value or "")
	return "".join(char for char in value if not unicodedata.combining(char)).casefold()


def _find_catalog_item(connection, message):
	text = _normalized(message)
	items = connection.agent_catalog_items.filter(
		business=connection.business,
		is_active=True,
	)
	if not items.exists():
		items = BusinessCatalogItem.objects.filter(business=connection.business, is_active=True)
	return next(
		(item for item in items.order_by("order", "-created_at") if _normalized(item.title) in text),
		None,
	)


def can_create_order(connection, contact, catalog_item, *, now=None):
	"""Check consent, tenant ownership, product existence and an allowed message path."""
	now = now or timezone.now()
	if contact.business_id != connection.business_id:
		return False, "contact_business_mismatch"
	if not contact.marketing_opt_in or not contact.consented_at or contact.opted_out_at:
		return False, "contact_consent_required"
	if catalog_item is None:
		return False, "catalog_item_required"
	if not BusinessCatalogItem.objects.filter(
		pk=catalog_item.pk,
		business=connection.business,
		is_active=True,
	).exists():
		return False, "catalog_item_unavailable"
	last_inbound_at = contact.last_inbound_at
	latest_message = BusinessWhatsAppMessage.objects.filter(
		contact=contact,
		direction=BusinessWhatsAppMessage.Direction.INBOUND,
	).order_by("-created_at").first()
	if latest_message:
		message_time = latest_message.meta_timestamp or latest_message.created_at
		if last_inbound_at is None or message_time > last_inbound_at:
			last_inbound_at = message_time
	if last_inbound_at and last_inbound_at >= now - timedelta(hours=24):
		return True, ""

	try:
		from .automations import get_approved_template_catalog

		templates = get_approved_template_catalog(connection.business)
	except Exception:
		logger.exception(
			"Impossible de valider un modèle Meta pour la commande (business_id=%s).",
			connection.business_id,
		)
		return False, "approved_template_unavailable"
	if templates:
		return True, ""
	return False, "message_window_expired"


@transaction.atomic
def create_order_safe(connection, contact, message, *, intent="commande", now=None):
	"""Record a guarded order request; never fabricate an account-bound checkout."""
	item = _find_catalog_item(connection, message)
	allowed, reason = can_create_order(connection, contact, item, now=now)
	pending_action = {
		"type": "payment" if intent == "paiement" else "order",
		"status": "pending_approval",
		"reason": reason or "business_confirmation_required",
		"catalog_item_id": item.pk if item else None,
		"catalog_item_title": item.title if item else "",
	}
	audit = BusinessWhatsAppAudit.objects.create(
		connection=connection,
		contact=contact,
		event_type="sales_action_pending",
		intent=intent,
		action=pending_action["type"],
		details={
			"status": "pending_approval",
			"guard_passed": allowed,
			"pending_action": pending_action,
		},
	)
	return {"status": "pending_approval", "pending_action": pending_action, "audit_id": audit.pk}


def record_sales_decision(connection, contact, decision, *, outcome="decided"):
	return BusinessWhatsAppAudit.objects.create(
		connection=connection,
		contact=contact,
		event_type="sales_decision",
		intent=decision["intention"],
		action=decision.get("action_next", ""),
		details={
			"outcome": outcome,
			"reply_length": len(decision.get("reponse", "")),
			"history_count": decision.get("history_count", 0),
			"qualification": contact.custom_fields.get("qualification", {}),
		},
	)


def resolve_action(connection, contact, decision):
	"""Describe a supported next step without creating an unconfirmed transaction."""
	intent = decision["intention"]
	if intent in {"commande", "paiement"}:
		return "pending_approval"
	if intent == "rdv":
		return "request_appointment_details"
	if decision.get("action_next") == "demander_budget":
		return "request_budget"
	return decision.get("action_next", "none")
