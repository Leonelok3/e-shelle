"""Safe adapter from sales intent to E-Shelle commerce actions."""

import logging
import re
import unicodedata
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from business.models import BusinessCatalogItem

from .models import (
	BusinessWhatsAppAudit,
	BusinessWhatsAppConnection,
	BusinessWhatsAppContact,
	BusinessWhatsAppMessage,
	WhatsAppDraftOrder,
)

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


def _extract_quantity(message):
	match = re.search(r"\b(\d{1,3})\s*(?:x|×|pcs?|pi[eè]ces?|unit[eé]s?)\b", message or "", re.I)
	return max(1, min(int(match.group(1)), 100)) if match else 1


def _catalog_price(item):
	match = re.search(r"\d[\d\s.,]*", item.price_label or "")
	digits = re.sub(r"\D", "", match.group(0)) if match else ""
	if not digits:
		return None
	try:
		return Decimal(digits)
	except InvalidOperation:
		return None


def _pending_action_audit(connection, contact, intent, reason, item=None):
	pending_action = {
		"type": "payment" if intent == "paiement" else "order",
		"status": "pending_approval",
		"reason": reason,
		"catalog_item_id": item.pk if item else None,
		"catalog_item_title": item.title if item else "",
	}
	audit = BusinessWhatsAppAudit.objects.create(
		connection=connection,
		contact=contact,
		event_type="sales_action_pending",
		intent=intent,
		action=pending_action["type"],
		details={"status": "pending_approval", "pending_action": pending_action},
	)
	return {"status": "pending_approval", "pending_action": pending_action, "audit_id": audit.pk}


def can_create_order(connection, contact, catalog_item, *, now=None):
	"""Check consent, tenant ownership, product existence and an allowed message path."""
	now = now or timezone.now()
	if (
		contact.business_id != connection.business_id
		or connection.status != BusinessWhatsAppConnection.Status.ACTIVE
	):
		return False, "contact_business_mismatch"
	if not contact.consent_service or contact.opted_out_at:
		return False, "service_consent_required"
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
	"""Create an auditable WhatsApp draft without creating an order before confirmation."""
	contact = BusinessWhatsAppContact.objects.select_for_update().get(pk=contact.pk)
	item = _find_catalog_item(connection, message)
	allowed, reason = can_create_order(connection, contact, item, now=now)
	if not allowed:
		return _pending_action_audit(connection, contact, intent, reason, item)
	unit_price = _catalog_price(item)
	if unit_price is None:
		return _pending_action_audit(connection, contact, intent, "catalog_price_requires_business_confirmation", item)

	quantity = _extract_quantity(message)
	draft = WhatsAppDraftOrder.objects.filter(
		contact=contact,
		status=WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION,
	).first()
	if draft:
		if draft.catalog_item_id == item.pk and draft.quantity == quantity:
			return {
				"status": draft.status,
				"draft": draft,
				"reponse": _draft_confirmation_text(draft),
			}
		draft.status = WhatsAppDraftOrder.Status.CANCELLED
		draft.audit = {**draft.audit, "cancel_reason": "replaced_by_new_draft"}
		draft.save(update_fields=["status", "audit"])

	draft = WhatsAppDraftOrder.objects.create(
		business=connection.business,
		connection=connection,
		contact=contact,
		catalog_item=item,
		quantity=quantity,
		unit_price=unit_price,
		total_price=unit_price * quantity,
		status=WhatsAppDraftOrder.Status.DRAFT,
		audit={"source": "whatsapp", "intent": intent, "idempotency_key": f"{contact.pk}:{item.pk}:{quantity}"},
	)
	draft.status = WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION
	draft.audit = {**draft.audit, "status_history": ["draft", "awaiting_confirmation"]}
	draft.save(update_fields=["status", "audit"])
	BusinessWhatsAppAudit.objects.create(
		connection=connection,
		contact=contact,
		event_type="draft_order_created",
		intent=intent,
		action="awaiting_confirmation",
		details={"draft_id": draft.pk, "catalog_item_id": item.pk, "quantity": quantity},
	)
	return {
		"status": draft.status,
		"draft": draft,
		"reponse": _draft_confirmation_text(draft),
	}


def _draft_confirmation_text(draft):
	first_name = (draft.contact.display_name or "").strip().split(" ")[0]
	greeting = f" {first_name}" if first_name else ""
	city = (
		draft.contact.custom_fields.get("qualification", {}).get("city")
		or draft.business.city
		or "à préciser"
	)
	return (
		f"Parfait{greeting}, tu veux {draft.catalog_item.title} x{draft.quantity} "
		f"à {_format_fcfa(draft.unit_price)} FCFA = {_format_fcfa(draft.total_price)} FCFA, "
		f"livraison {city} ? Réponds OUI pour confirmer."
	)


def _format_fcfa(amount):
	return f"{amount:,.0f}".replace(",", " ")


def is_explicit_draft_confirmation(contact, value):
	value = str(value or "").strip()
	if _normalized(value) in {"oui", "oui confirme", "oui je confirme"}:
		return contact.draft_orders.filter(
			status=WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION,
		).exists()
	try:
		from uuid import UUID

		token = UUID(value)
	except (TypeError, ValueError):
		return False
	return contact.draft_orders.filter(
		confirmation_token=token,
		status=WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION,
	).exists()


@transaction.atomic
def confirm_draft_order(contact_phone, token_ou_oui, *, business=None):
	"""Confirm only an explicit OUI/token; idempotently create the manual-payment handoff."""
	from boutique.models import Commande, LigneCommande
	from payments.models import Transaction

	value = str(token_ou_oui or "").strip()
	is_yes = _normalized(value) in {"oui", "oui confirme", "oui je confirme"}
	contact_query = BusinessWhatsAppContact.objects.filter(phone=contact_phone)
	if business is not None:
		contact_query = contact_query.filter(business=business)
	contacts = list(contact_query[:2])
	if len(contacts) > 1 and business is None:
		return {"status": "business_required"}
	contact = contacts[0] if contacts else None
	if not contact:
		return {"status": "not_found"}
	if contact.opted_out_at or not contact.consent_service:
		return {"status": "consent_required"}
	if is_yes:
		draft_query = WhatsAppDraftOrder.objects.select_for_update().filter(
			contact=contact,
			status__in=[
				WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION,
				WhatsAppDraftOrder.Status.CONFIRMED,
			],
		)
	else:
		try:
			from uuid import UUID

			token = UUID(value)
			draft_query = WhatsAppDraftOrder.objects.select_for_update().filter(
				contact=contact,
				confirmation_token=token,
			)
		except (TypeError, ValueError):
			return {"status": "explicit_confirmation_required"}
	draft = draft_query.order_by("-created_at", "-pk").first()
	if draft is None:
		return {"status": "explicit_confirmation_required"}
	if not is_yes and str(draft.confirmation_token) != value:
		return {"status": "explicit_confirmation_required"}
	if draft.status == WhatsAppDraftOrder.Status.CONFIRMED:
		order = getattr(draft, "boutique_order", None)
		payment = getattr(draft, "payment_transaction", None)
		if order and payment:
			return {"status": "already_confirmed", "draft": draft, "order": order, "transaction": payment}
		return {"status": "confirmation_incomplete"}
	if draft.status != WhatsAppDraftOrder.Status.AWAITING_CONFIRMATION:
		return {"status": "draft_not_awaiting_confirmation"}

	order = Commande.objects.create(
		utilisateur=None,
		business_profile=draft.business,
		whatsapp_contact=contact,
		whatsapp_draft_order=draft,
		source="whatsapp_confirmed",
		statut="en_attente",
		montant_total=draft.total_price,
		telephone=contact.phone,
		notes=f"Commande WhatsApp confirmée; article catalogue Business #{draft.catalog_item_id}.",
	)
	LigneCommande.objects.create(
		commande=order,
		produit=None,
		business_catalog_item=draft.catalog_item,
		quantite=draft.quantity,
		prix_unit=draft.unit_price,
	)
	payment = Transaction.objects.create(
		utilisateur=None,
		type_tx="service",
		methode="mtn_momo",
		montant=draft.total_price,
		devise="XAF",
		telephone=contact.phone,
		statut="pending_awaiting_manual_validation",
		commande=order,
		whatsapp_draft_order=draft,
		payment_link=draft.business.whatsapp_url(
			text=(
				f"Bonjour {draft.business.name}, je souhaite régler la commande "
				f"{order.reference} de {_format_fcfa(draft.total_price)} FCFA. "
				"Merci de me confirmer les modalités Mobile Money."
			)
		),
		metadata={
			"source": "whatsapp_confirmed",
			"business_id": draft.business_id,
			"draft_id": draft.pk,
			"manual_validation_required": True,
			"payment_link_kind": "business_whatsapp_contact",
		},
	)
	draft.status = WhatsAppDraftOrder.Status.CONFIRMED
	draft.confirmed_at = timezone.now()
	draft.audit = {
		**draft.audit,
		"status_history": [*draft.audit.get("status_history", []), "confirmed"],
		"order_id": order.pk,
		"transaction_id": payment.pk,
	}
	draft.save(update_fields=["status", "confirmed_at", "audit"])
	BusinessWhatsAppAudit.objects.create(
		connection=draft.connection,
		contact=contact,
		event_type="draft_order_confirmed",
		intent="commande",
		action="manual_payment_handoff",
		details={
			"draft_id": draft.pk,
			"order_id": order.pk,
			"transaction_id": payment.pk,
			"confirmation": "customer_explicit",
		},
	)
	return {"status": "confirmed", "draft": draft, "order": order, "transaction": payment}


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
	if decision.get("pending_action", {}).get("status") == "awaiting_confirmation":
		return "await_customer_confirmation"
	if intent in {"commande", "paiement"}:
		return "pending_approval"
	if intent == "rdv":
		return "request_appointment_details"
	if decision.get("action_next") == "demander_budget":
		return "request_budget"
	return decision.get("action_next", "none")
