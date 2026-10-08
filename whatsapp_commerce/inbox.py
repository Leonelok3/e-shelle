"""Tenant-isolated WhatsApp inbox and webhook processing."""

from datetime import datetime, timedelta, timezone as datetime_timezone

from django.db import transaction
from django.utils import timezone

from .models import (
	BusinessWhatsAppConnection,
	BusinessWhatsAppContact,
	BusinessWhatsAppMessage,
	ScheduledBusinessWhatsAppMessage,
)
from .onboarding import MetaOnboardingError, _request_meta
from .services import normalize_phone
from .entitlements import require_whatsapp_entitlement


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
		return

	contact, _ = BusinessWhatsAppContact.objects.get_or_create(
		business=connection.business,
		phone=phone,
	)
	contact.display_name = display_name or contact.display_name
	contact.last_inbound_at = received_at or timezone.now()
	body = _inbound_text(message)
	did_opt_out = body.casefold() in {"stop", "arret", "arrêt", "desinscrire", "désinscrire", "unsubscribe"}
	if did_opt_out:
		contact.marketing_opt_in = False
		contact.opted_out_at = received_at or timezone.now()
	BusinessWhatsAppContact.objects.filter(pk=contact.pk).update(
		display_name=contact.display_name,
		last_inbound_at=contact.last_inbound_at,
		marketing_opt_in=contact.marketing_opt_in,
		opted_out_at=contact.opted_out_at,
		last_activity_at=timezone.now(),
	)
	if did_opt_out:
		from .automations import cancel_scheduled_contact_messages

		cancel_scheduled_contact_messages(contact, "Le contact a envoyé une demande STOP.")
	BusinessWhatsAppMessage.objects.get_or_create(
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
					_save_inbound(
						connection,
						message,
						names.get(str(message.get("from", "")), ""),
						_message_datetime(message.get("timestamp")),
					)

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
