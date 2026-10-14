"""Tenant-isolated WhatsApp inbox and webhook processing."""

import logging
from datetime import datetime, timedelta, timezone as datetime_timezone

from django.db import transaction
from django.utils import timezone

from .models import (
	BusinessWhatsAppAudit,
	BusinessWhatsAppConnection,
	BusinessWhatsAppContact,
	BusinessWhatsAppMessage,
	ScheduledBusinessWhatsAppMessage,
)
from .onboarding import MetaOnboardingError, _request_meta
from .services import normalize_phone
from .entitlements import require_whatsapp_entitlement

logger = logging.getLogger(__name__)


def _message_datetime(value):
	try:
		return datetime.fromtimestamp(int(value), tz=datetime_timezone.utc)
	except (TypeError, ValueError, OverflowError):
		return None


def _inbound_text(message):
	message_type = message.get("type", "text")
	if message_type == "text":
		return (message.get("text", {}).get("body") or "").strip()
	if message_type == "button":
		return (message.get("button", {}).get("text") or "").strip()
	if message_type == "interactive":
		interactive = message.get("interactive", {})
		reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
		return (reply.get("title") or "").strip()
	if message_type in {"image", "audio", "document", "video", "sticker"}:
		media = message.get(message_type, {})
		return (media.get("caption") or media.get("filename") or f"[{message_type}]").strip()
	return ""


@transaction.atomic
def _save_inbound(connection, message, display_name, received_at):
	phone = normalize_phone(message.get("from", ""))
	message_id = message.get("id", "")
	if not phone or not message_id:
		return None, None, False

	contact, _ = BusinessWhatsAppContact.objects.get_or_create(
		business=connection.business,
		phone=phone,
	)
	contact.display_name = display_name or contact.display_name
	contact.last_inbound_at = received_at or timezone.now()
	body = _inbound_text(message)
	did_opt_out = body.casefold() in {"stop", "arret", "arrêt", "desinscrire", "désinscrire", "unsubscribe"}
	consent_marketing = body.casefold() in {"oui pub", "oui promotions", "oui marketing"}
	contact.consent_service = True
	if consent_marketing:
		contact.consent_marketing = True
		contact.marketing_opt_in = True
		contact.consent_source = "WhatsApp: réponse OUI PUB"
		contact.consented_at = received_at or timezone.now()
	if did_opt_out:
		contact.marketing_opt_in = False
		contact.consent_marketing = False
		contact.opted_out_at = received_at or timezone.now()
	BusinessWhatsAppContact.objects.filter(pk=contact.pk).update(
		display_name=contact.display_name,
		last_inbound_at=contact.last_inbound_at,
		marketing_opt_in=contact.marketing_opt_in,
		consent_service=contact.consent_service,
		consent_marketing=contact.consent_marketing,
		consent_source=contact.consent_source,
		consented_at=contact.consented_at,
		opted_out_at=contact.opted_out_at,
		last_activity_at=timezone.now(),
	)
	if did_opt_out:
		from .automations import cancel_scheduled_contact_messages

		cancel_scheduled_contact_messages(contact, "Le contact a envoyé une demande STOP.")
		BusinessWhatsAppAudit.objects.create(
			connection=connection,
			contact=contact,
			event_type="contact_opted_out",
			action="stop_keyword",
			details={"message_id": message_id},
		)
	elif consent_marketing:
		BusinessWhatsAppAudit.objects.create(
			connection=connection,
			contact=contact,
			event_type="marketing_consent_granted",
			action="whatsapp_oui_pub",
			details={"message_id": message_id},
		)
	saved_message, created = BusinessWhatsAppMessage.objects.get_or_create(
		wa_message_id=message_id,
		defaults={
			"contact": contact,
			"direction": BusinessWhatsAppMessage.Direction.INBOUND,
			"message_type": message.get("type", "text"),
			"body": body,
			"status": "received",
			"meta_timestamp": received_at,
		},
	)
	if created and not did_opt_out:
		from .automations import cancel_scheduled_contact_messages

		cancel_scheduled_contact_messages(
			contact,
			"Le contact a répondu; les relances précédentes sont annulées.",
		)
	return contact, saved_message, created


def _run_sales_agent(connection, contact, inbound_message):
	from django.conf import settings

	if (
		not getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False)
		or not connection.agent_enabled
		or contact.opted_out_at
	):
		return

	from .entitlements import require_whatsapp_entitlement
	from .funnel import build_funnel_reply
	from .orchestrator import record_sales_decision, resolve_action

	try:
		if not require_whatsapp_entitlement(contact.business, "can_use_crm"):
			return
		from .orchestrator import confirm_draft_order, is_explicit_draft_confirmation

		if is_explicit_draft_confirmation(contact, inbound_message.body):
			confirmation = confirm_draft_order(contact.phone, inbound_message.body, business=contact.business)
			if confirmation.get("status") == "already_confirmed":
				return
			if confirmation.get("status") == "confirmed":
				draft = confirmation["draft"]
				order = confirmation["order"]
				reply = (
					f"Commande #{order.reference} confirmée. "
					f"{contact.business.name} va te contacter pour le paiement Mobile Money "
					"et la livraison. Merci !"
				)
				message_id = send_business_reply(contact, reply)
				BusinessWhatsAppAudit.objects.create(
					connection=connection,
					contact=contact,
					event_type="sales_order_handoff_sent",
					intent="commande",
					action="manual_payment_handoff",
					details={
						"draft_id": draft.pk,
						"order_id": order.pk,
						"transaction_id": confirmation["transaction"].pk,
						"wa_message_id": message_id,
					},
				)
				return
		decision = build_funnel_reply(connection, contact, inbound_message)
		action = resolve_action(connection, contact, decision)
		decision["action_next"] = action
		audit = record_sales_decision(connection, contact, decision)
		message_id = send_business_reply(contact, decision["reponse"])
		audit.details = {
			**audit.details,
			"outcome": "sent",
			"wa_message_id": message_id,
		}
		audit.save(update_fields=["details"])
		from .automations import schedule_sales_follow_ups

		try:
			schedule_sales_follow_ups(contact)
		except Exception:
			logger.exception(
				"WhatsApp Commerce: planification des relances échouée (business_id=%s, contact_id=%s).",
				connection.business_id,
				contact.pk,
			)
	except Exception as exc:
		logger.exception(
			"WhatsApp Commerce: agent vendeur en échec (business_id=%s, contact_id=%s).",
			connection.business_id,
			contact.pk,
		)
		BusinessWhatsAppAudit.objects.create(
			connection=connection,
			contact=contact,
			event_type="sales_agent_error",
			action="reply_failed",
			details={"error_type": type(exc).__name__, "message": str(exc)[:400]},
		)


def _record_template_status_update(connection, value):
	BusinessWhatsAppAudit.objects.create(
		connection=connection,
		event_type="message_template_status_update",
		action=str(value.get("event", "unknown"))[:64],
		details={
			"template_name": str(value.get("message_template_name", ""))[:128],
			"template_language": str(value.get("message_template_language", ""))[:32],
			"template_id": str(value.get("message_template_id", ""))[:64],
			"reason": str(value.get("reason", ""))[:300],
		},
	)


def process_business_whatsapp_webhook(payload):
	"""Persist inbound messages only for the connection matching both Meta IDs."""
	for entry in payload.get("entry", []):
		if not isinstance(entry, dict):
			continue
		waba_id = str(entry.get("id", ""))
		for change in entry.get("changes", []):
			if not isinstance(change, dict):
				continue
			value = change.get("value", {})
			if not isinstance(value, dict):
				continue
			if change.get("field") == "message_template_status_update":
				template_connection = BusinessWhatsAppConnection.objects.filter(
					waba_id=waba_id,
					status=BusinessWhatsAppConnection.Status.ACTIVE,
				).first()
				if template_connection:
					_record_template_status_update(template_connection, value)
				continue
			metadata = value.get("metadata", {})
			phone_id = str(metadata.get("phone_number_id", "")) if isinstance(metadata, dict) else ""
			connection = BusinessWhatsAppConnection.objects.filter(
				waba_id=waba_id,
				phone_number_id=phone_id,
				status=BusinessWhatsAppConnection.Status.ACTIVE,
			).select_related("business").first()
			if connection is None:
				continue

			names = {}
			for item in value.get("contacts", []):
				if isinstance(item, dict) and item.get("wa_id"):
					names[str(item["wa_id"])] = str(item.get("profile", {}).get("name", ""))[:180]

			for message in value.get("messages", []):
				if isinstance(message, dict):
					contact, saved_message, created = _save_inbound(
						connection,
						message,
						names.get(str(message.get("from", "")), ""),
						_message_datetime(message.get("timestamp")),
					)
					if created and contact and saved_message and not contact.opted_out_at:
						_run_sales_agent(connection, contact, saved_message)

			for status in value.get("statuses", []):
				if not isinstance(status, dict) or not status.get("id"):
					continue
				BusinessWhatsAppMessage.objects.filter(
					wa_message_id=status["id"],
					contact__business=connection.business,
					direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
				).update(status=str(status.get("status", ""))[:24])
				ScheduledBusinessWhatsAppMessage.objects.filter(
					wa_message_id=status["id"],
					connection=connection,
				).update(delivery_status=str(status.get("status", ""))[:24])


def is_business_whatsapp_connection(waba_id, phone_number_id):
	return BusinessWhatsAppConnection.objects.filter(
		waba_id=str(waba_id or ""),
		phone_number_id=str(phone_number_id or ""),
		status=BusinessWhatsAppConnection.Status.ACTIVE,
	).exists()


def send_business_reply(contact, text):
	"""Send a customer-service reply within the WhatsApp 24-hour window only."""
	if contact.opted_out_at:
		raise MetaOnboardingError("Ce contact a demandé à ne plus recevoir de messages.")
	if not require_whatsapp_entitlement(contact.business, "can_use_crm"):
		raise MetaOnboardingError("L’inbox WhatsApp nécessite une formule Business active.")
	connection = BusinessWhatsAppConnection.objects.filter(
		business=contact.business,
		status=BusinessWhatsAppConnection.Status.ACTIVE,
	).first()
	if connection is None or not connection.get_access_token():
		raise MetaOnboardingError("Connectez d’abord le compte WhatsApp Business.")
	if not contact.last_inbound_at or contact.last_inbound_at < timezone.now() - timedelta(hours=24):
		raise MetaOnboardingError("La fenêtre de réponse de 24 h est fermée. Utilisez un modèle approuvé par Meta.")
	if not text or len(text) > 4096:
		raise MetaOnboardingError("Le message doit contenir entre 1 et 4096 caractères.")

	result = _request_meta(
		"POST",
		f"{connection.phone_number_id}/messages",
		token=connection.get_access_token(),
		payload={
			"messaging_product": "whatsapp",
			"recipient_type": "individual",
			"to": contact.phone.lstrip("+"),
			"type": "text",
			"text": {"body": text, "preview_url": False},
		},
	)
	messages = result.get("messages", [])
	if not messages or not messages[0].get("id"):
		raise MetaOnboardingError("Meta n’a pas confirmé la prise en charge du message.")
	message_id = str(messages[0]["id"])
	BusinessWhatsAppMessage.objects.create(
		contact=contact,
		wa_message_id=message_id,
		direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
		message_type="text",
		body=text,
		status="sent",
		meta_timestamp=timezone.now(),
	)
	BusinessWhatsAppContact.objects.filter(pk=contact.pk).update(last_activity_at=timezone.now())
	return message_id
