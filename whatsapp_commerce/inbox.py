"""Tenant-isolated WhatsApp inbox and webhook processing."""

import logging
from datetime import datetime, timedelta, timezone as datetime_timezone

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from business.models import BusinessProfile

from .activation import TEST_SUFFIX
from .models import (
	BusinessWhatsAppActivation,
	BusinessWhatsAppAudit,
	BusinessWhatsAppConnection,
	BusinessWhatsAppContact,
	BusinessWhatsAppMessage,
	BusinessWhatsAppReplyJob,
	ScheduledBusinessWhatsAppMessage,
)
from .onboarding import MetaOnboardingError, _request_meta
from .services import normalize_phone
from .entitlements import require_whatsapp_entitlement
from whatsapp_agent.models import MessageEnvoi

logger = logging.getLogger(__name__)


class AutomatedReplySuppressed(MetaOnboardingError):
	"""The reply did not reach Meta because it was blocked locally."""


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

	body = _inbound_text(message)
	test_marker = TEST_SUFFIX.search(body)
	if not test_marker and "[eshelle-test:" in body.casefold():
		return None, None, False
	activation = None
	if test_marker:
		activation = BusinessWhatsAppActivation.objects.select_for_update().filter(
			connection=connection,
			test_code=test_marker.group(1).lower(),
			test_sender=phone,
			test_phone_number_id=connection.phone_number_id,
			test_expires_at__gt=timezone.now(),
			test_message__isnull=True,
		).first()
		if activation is None:
			return None, None, False
		body = body[:test_marker.start()].strip()

	contact, _ = BusinessWhatsAppContact.objects.get_or_create(
		business=connection.business,
		phone=phone,
	)
	contact = BusinessWhatsAppContact.objects.select_for_update().get(pk=contact.pk)
	audio = message.get("audio")
	media_id = str(audio.get("id") or "")[:80] if message.get("type") == "audio" and isinstance(audio, dict) else ""
	saved_message, created = BusinessWhatsAppMessage.objects.get_or_create(
		wa_message_id=message_id,
		defaults={
			"contact": contact,
			"direction": BusinessWhatsAppMessage.Direction.INBOUND,
			"message_type": message.get("type", "text"),
			"media_id": media_id,
			"body": body,
			"status": "received",
			"meta_timestamp": received_at,
			"is_activation_test": activation is not None,
		},
	)
	if not created:
		return contact, saved_message, False

	contact.display_name = display_name or contact.display_name
	inbound_at = received_at or timezone.now()
	contact.last_inbound_at = max(contact.last_inbound_at or inbound_at, inbound_at)
	if activation:
		BusinessWhatsAppContact.objects.filter(pk=contact.pk).update(last_inbound_at=contact.last_inbound_at)
		activation.test_message = saved_message
		activation.save(update_fields=["test_message"])
		BusinessWhatsAppReplyJob.objects.create(
			message=saved_message, connection=connection, phone_number_id=connection.phone_number_id,
			activation_code=activation.test_code,
		)
		return contact, saved_message, True

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
	if not did_opt_out:
		from .automations import cancel_scheduled_contact_messages

		cancel_scheduled_contact_messages(
			contact,
			"Le contact a répondu; les relances précédentes sont annulées.",
		)
		if not contact.opted_out_at and not contact.agent_paused:
			BusinessWhatsAppReplyJob.objects.create(
				message=saved_message, connection=connection, phone_number_id=connection.phone_number_id,
			)
	return contact, saved_message, created


def _refund_ai_credit(business):
	BusinessProfile.objects.filter(
		pk=business.pk,
		plan=business.plan,
		subscription_expires_at=business.subscription_expires_at,
		subscription_expires_at__gt=timezone.now(),
		is_active=True,
		is_trial=False,
	).update(ai_credits=F("ai_credits") + 1, updated_at=timezone.now())


def _reserve_ai_credit(business):
	return BusinessProfile.objects.filter(
		pk=business.pk,
		plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
		plan=business.plan,
		is_active=True,
		is_trial=False,
		subscription_expires_at=business.subscription_expires_at,
		subscription_expires_at__gt=timezone.now(),
		ai_credits__gt=0,
	).update(ai_credits=F("ai_credits") - 1, updated_at=timezone.now())


def _run_sales_agent(connection, contact, inbound_message, *, reply_job_id=None):
	from django.conf import settings

	if (
		not getattr(settings, "WHATSAPP_COMMERCE_AI_ENABLED", False)
		or not connection.agent_enabled
		or contact.opted_out_at
		or contact.agent_paused
	):
		return BusinessWhatsAppReplyJob.Status.SKIPPED

	from .entitlements import require_whatsapp_entitlement
	from .funnel import build_funnel_reply
	from .orchestrator import record_sales_decision, resolve_action

	business = contact.business
	if not require_whatsapp_entitlement(business, "can_use_crm"):
		return BusinessWhatsAppReplyJob.Status.SKIPPED
	if not _reserve_ai_credit(business):
		BusinessWhatsAppAudit.objects.create(
			connection=connection,
			contact=contact,
			event_type="sales_agent_credits_exhausted",
			action="reply_skipped",
			details={"reason": "No active AI credits."},
		)
		return BusinessWhatsAppReplyJob.Status.SKIPPED

	send_attempted = False
	try:
		from .orchestrator import confirm_draft_order, is_explicit_draft_confirmation

		if is_explicit_draft_confirmation(contact, inbound_message.body):
			confirmation = confirm_draft_order(contact.phone, inbound_message.body, business=contact.business)
			if confirmation.get("status") == "already_confirmed":
				_refund_ai_credit(business)
				return BusinessWhatsAppReplyJob.Status.SKIPPED
			if confirmation.get("status") == "confirmed":
				from .checkout import checkout_url

				draft = confirmation["draft"]
				order = confirmation["order"]
				payment = confirmation["transaction"]
				reply = (
					f"Commande #{order.reference} confirmée. "
					f"{contact.business.name} va te contacter pour le paiement Mobile Money "
					"et la livraison. Merci !"
				)
				if payment.methode == "campay":
					reply = f"Commande #{order.reference} confirmée. Pour régler par Mobile Money : {checkout_url(payment)}"
				send_attempted = True
				message_id = send_business_reply(
					contact, reply, expected_phone_number_id=connection.phone_number_id, reply_job_id=reply_job_id,
					require_agent_enabled=True,
				)
				BusinessWhatsAppAudit.objects.create(
					connection=connection,
					contact=contact,
					event_type="sales_order_handoff_sent",
					intent="commande",
					action="campay_checkout" if payment.methode == "campay" else "manual_payment_handoff",
					details={
						"draft_id": draft.pk,
						"order_id": order.pk,
						"transaction_id": confirmation["transaction"].pk,
						"wa_message_id": message_id,
					},
				)
				return BusinessWhatsAppReplyJob.Status.SENT
		decision = build_funnel_reply(connection, contact, inbound_message)
		action = resolve_action(connection, contact, decision)
		decision["action_next"] = action
		audit = record_sales_decision(connection, contact, decision)
		send_attempted = True
		message_id = send_business_reply(
			contact, decision["reponse"], expected_phone_number_id=connection.phone_number_id, reply_job_id=reply_job_id,
			require_agent_enabled=True,
		)
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
		return BusinessWhatsAppReplyJob.Status.SENT
	except AutomatedReplySuppressed:
		_refund_ai_credit(business)
		return BusinessWhatsAppReplyJob.Status.SKIPPED
	except Exception as exc:
		# A timeout or failure after dispatch may still represent an accepted Meta send.
		if not send_attempted:
			_refund_ai_credit(business)
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
			details={"error_type": type(exc).__name__, "send_attempted": send_attempted},
		)
		return BusinessWhatsAppReplyJob.Status.REVIEW


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
					_save_inbound(
						connection,
						message,
						names.get(str(message.get("from", "")), ""),
						_message_datetime(message.get("timestamp")),
					)

			for status in value.get("statuses", []):
				if not isinstance(status, dict) or not status.get("id"):
					continue
				wa_status = str(status.get("status", ""))[:24]
				outbound = BusinessWhatsAppMessage.objects.filter(
					wa_message_id=status["id"],
					contact__business=connection.business,
					direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
				)
				outbound.filter(is_activation_test=False).update(status=wa_status)
				test_previous_statuses = {
					"sent": ["accepted"],
					"delivered": ["accepted", "sent", "failed"],
					"read": ["accepted", "sent", "delivered", "failed"],
					"failed": ["accepted", "sent"],
				}
				if wa_status in test_previous_statuses:
					outbound.filter(is_activation_test=True, status__in=test_previous_statuses[wa_status]).update(status=wa_status)
				ScheduledBusinessWhatsAppMessage.objects.filter(
					wa_message_id=status["id"],
					connection=connection,
				).update(delivery_status=wa_status)

				campaign_status = {
					"sent": MessageEnvoi.STATUT_ENVOYE,
					"delivered": MessageEnvoi.STATUT_LIVRE,
					"read": MessageEnvoi.STATUT_LU,
					"failed": MessageEnvoi.STATUT_ECHEC,
				}.get(wa_status)
				if campaign_status:
					campaign_messages = MessageEnvoi.objects.filter(
						whatsapp_message_id=status["id"],
						business_contact__business=connection.business,
					).select_related("campagne")
					changed_campaigns = set()
					for campaign_message in campaign_messages:
						if campaign_message.statut in {
							MessageEnvoi.STATUT_LU,
							MessageEnvoi.STATUT_ECHEC,
						} and campaign_status != MessageEnvoi.STATUT_LU:
							continue
						campaign_message.statut = campaign_status
						if campaign_status == MessageEnvoi.STATUT_ECHEC:
							campaign_message.erreur = str(status.get("errors", ""))[:2000]
						campaign_message.save(
							update_fields=["statut", "erreur", "mis_a_jour_le"]
						)
						changed_campaigns.add(campaign_message.campagne)
					if changed_campaigns:
						from whatsapp_agent.tasks import recalculer_stats_campagne

						for campaign in changed_campaigns:
							recalculer_stats_campagne(campaign)


def is_business_whatsapp_connection(waba_id, phone_number_id):
	return BusinessWhatsAppConnection.objects.filter(
		waba_id=str(waba_id or ""),
		phone_number_id=str(phone_number_id or ""),
		status=BusinessWhatsAppConnection.Status.ACTIVE,
	).exists()


def send_business_reply(
	contact, text, *, expected_phone_number_id=None, reply_job_id=None,
	activation_test=False, require_agent_enabled=False,
):
	"""Send a customer-service reply within the WhatsApp 24-hour window only."""
	if expected_phone_number_id is not None:
		contact.refresh_from_db(fields=["agent_paused", "opted_out_at", "last_inbound_at", "business"])
		if contact.agent_paused or contact.opted_out_at:
			raise AutomatedReplySuppressed("La réponse automatique a été désactivée pour ce contact.")
	error_class = AutomatedReplySuppressed if expected_phone_number_id is not None else MetaOnboardingError
	if contact.opted_out_at:
		raise error_class("Ce contact a demandé à ne plus recevoir de messages.")
	if not require_whatsapp_entitlement(contact.business, "can_use_crm"):
		raise error_class("L’inbox WhatsApp nécessite une formule Business active.")
	connections = BusinessWhatsAppConnection.objects.filter(
		business=contact.business,
		status=BusinessWhatsAppConnection.Status.ACTIVE,
	)
	if expected_phone_number_id is not None:
		connections = connections.filter(phone_number_id=expected_phone_number_id)
	connection = connections.first()
	token = connection.get_access_token() if connection else ""
	if not token:
		raise error_class("Connectez d’abord le compte WhatsApp Business.")
	if require_agent_enabled and not connection.agent_enabled:
		raise AutomatedReplySuppressed("Les réponses automatiques de cette entreprise sont en pause.")
	if not contact.last_inbound_at or contact.last_inbound_at < timezone.now() - timedelta(hours=24):
		raise error_class("La fenêtre de réponse de 24 h est fermée. Utilisez un modèle approuvé par Meta.")
	if not text or len(text) > 4096:
		raise error_class("Le message doit contenir entre 1 et 4096 caractères.")
	if reply_job_id is not None and not BusinessWhatsAppReplyJob.objects.filter(
		pk=reply_job_id, message__contact=contact, status=BusinessWhatsAppReplyJob.Status.PROCESSING,
	).exists():
		raise AutomatedReplySuppressed("Cette réponse est passée en revue manuelle.")

	result = _request_meta(
		"POST",
		f"{connection.phone_number_id}/messages",
		token=token,
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
		status="accepted" if activation_test else "sent",
		meta_timestamp=timezone.now(),
		is_activation_test=activation_test,
	)
	BusinessWhatsAppContact.objects.filter(pk=contact.pk).update(last_activity_at=timezone.now())
	return message_id
