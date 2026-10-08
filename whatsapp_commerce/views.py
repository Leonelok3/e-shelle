import logging
import json
import secrets
import time

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q

from business.models import BusinessProfile
from .automations import (
	cancel_scheduled_contact_messages,
	get_approved_template_catalog,
	schedule_template_follow_up,
)
from .business_catalog import sync_business_catalog as sync_business_catalog_items
from .entitlements import whatsapp_entitlements
from .inbox import send_business_reply
from .models import (
	BusinessCatalogWhatsAppSync,
	BusinessWhatsAppConnection,
	BusinessWhatsAppContact,
	BusinessWhatsAppMessage,
	ProductView,
	ScheduledBusinessWhatsAppMessage,
)
from .onboarding import MetaOnboardingError, connect_business, retry_connection_setup
from .services import get_whatsapp_order_url, normalize_phone

logger = logging.getLogger(__name__)


def _owned_business(request, business_id):
	return get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)


@login_required
@require_GET
def business_whatsapp_dashboard(request, business_id):
	business = _owned_business(request, business_id)
	entitlements = whatsapp_entitlements(business)
	connection = BusinessWhatsAppConnection.objects.filter(business=business).first()
	contacts = BusinessWhatsAppContact.objects.filter(business=business)
	status_filter = request.GET.get("status", "")
	query = request.GET.get("q", "").strip()[:100]
	if not entitlements["can_use_crm"]:
		contacts = contacts.none()
	if status_filter in dict(BusinessWhatsAppContact.PipelineStatus.choices):
		contacts = contacts.filter(pipeline_status=status_filter)
	else:
		status_filter = ""
	if query:
		contacts = contacts.filter(
			Q(display_name__icontains=query) | Q(phone__icontains=query)
		)
	contact = None
	contact_id = request.GET.get("contact")
	if contact_id and entitlements["can_use_crm"]:
		contact = contacts.filter(pk=contact_id).first()
	catalog_syncs = BusinessCatalogWhatsAppSync.objects.filter(
		connection=connection,
	).select_related("business_catalog_item")[:50] if connection else []
	return render(
		request,
		"whatsapp_commerce/business_dashboard.html",
		{
			"business": business,
			"connection": connection,
			"contacts": contacts[:100],
			"selected_contact": contact,
			"conversation_messages": contact.messages.all()[:100] if contact else [],
			"entitlements": entitlements,
			"status_choices": BusinessWhatsAppContact.PipelineStatus.choices,
			"status_filter": status_filter,
			"search_query": query,
			"catalog_syncs": catalog_syncs,
			"catalog_item_count": business.catalog_items.count(),
			"automations_enabled": getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False),
			"scheduled_messages": (
				contact.scheduled_messages.all()[:10] if contact else []
			),
			"signup_configured": bool(
				getattr(settings, "WHATSAPP_TECH_PROVIDER_APP_ID", "")
				and getattr(settings, "WHATSAPP_TECH_PROVIDER_APP_SECRET", "")
				and getattr(settings, "WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID", "")
			),
		},
	)


@login_required
@require_GET
def start_business_connection(request, business_id):
	business = _owned_business(request, business_id)
	if not whatsapp_entitlements(business)["can_connect"]:
		messages.error(request, "La connexion WhatsApp nécessite une formule Pro active ou l’essai Business.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	connection = BusinessWhatsAppConnection.objects.filter(business=business).first()
	if connection and connection.status != BusinessWhatsAppConnection.Status.DISCONNECTED:
		messages.info(request, "Un compte WhatsApp est déjà associé à cette fiche.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	state = secrets.token_urlsafe(32)
	request.session["wa_embedded_signup"] = {
		"state": state,
		"business_id": business.pk,
		"issued_at": int(time.time()),
	}
	return render(
		request,
		"whatsapp_commerce/business_connect.html",
		{
			"business": business,
			"state": state,
			"signup_configured": bool(
				getattr(settings, "WHATSAPP_TECH_PROVIDER_APP_ID", "")
				and getattr(settings, "WHATSAPP_TECH_PROVIDER_APP_SECRET", "")
				and getattr(settings, "WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID", "")
			),
			"app_id": getattr(settings, "WHATSAPP_TECH_PROVIDER_APP_ID", ""),
			"config_id": getattr(settings, "WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID", ""),
			"graph_api_version": getattr(settings, "WHATSAPP_GRAPH_API_VERSION", "v25.0"),
		},
	)


@login_required
@require_POST
def complete_business_connection(request, business_id):
	business = _owned_business(request, business_id)
	if not whatsapp_entitlements(business)["can_connect"]:
		return JsonResponse({"error": "Une formule Pro active est requise pour connecter WhatsApp."}, status=403)
	if request.content_type != "application/json":
		return JsonResponse({"error": "Content-Type application/json requis."}, status=415)
	try:
		data = json.loads(request.body.decode("utf-8"))
	except (UnicodeDecodeError, json.JSONDecodeError):
		return JsonResponse({"error": "Données de connexion invalides."}, status=400)
	if not isinstance(data, dict):
		return JsonResponse({"error": "Données de connexion invalides."}, status=400)

	session = request.session.get("wa_embedded_signup", {})
	state = data.get("state", "")
	try:
		issued_at = int(session.get("issued_at", 0)) if isinstance(session, dict) else 0
	except (TypeError, ValueError):
		issued_at = 0
	if (
		not isinstance(session, dict)
		or session.get("business_id") != business.pk
		or not secrets.compare_digest(str(session.get("state", "")), str(state))
		or int(time.time()) - issued_at > 900
		or data.get("event") != "FINISH"
	):
		return JsonResponse({"error": "Cette session Meta a expiré. Relancez la connexion."}, status=403)

	try:
		connection, ready = connect_business(
			business,
			code=data.get("code", ""),
			waba_id=data.get("waba_id", ""),
			phone_number_id=data.get("phone_number_id", ""),
			meta_business_id=data.get("business_id", ""),
			pin=data.get("pin", ""),
		)
	except MetaOnboardingError as exc:
		return JsonResponse({"error": str(exc)}, status=400)
	except IntegrityError:
		return JsonResponse(
			{"error": "Ce compte ou numéro WhatsApp vient d’être relié à une autre fiche E-Shelle."},
			status=409,
		)
	del request.session["wa_embedded_signup"]
	request.session.modified = True

	if ready:
		return JsonResponse({"ok": True, "redirect": reverse("whatsapp_commerce:business_dashboard", args=[business.pk])})
	return JsonResponse(
		{
			"ok": False,
			"pending": True,
			"error": connection.last_error,
			"redirect": reverse("whatsapp_commerce:business_dashboard", args=[business.pk]),
		},
		status=202,
	)


@login_required
@require_POST
def retry_business_connection(request, business_id):
	business = _owned_business(request, business_id)
	if not whatsapp_entitlements(business)["can_connect"]:
		messages.error(request, "Une formule Pro active est requise pour reprendre la connexion WhatsApp.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	connection = get_object_or_404(
		BusinessWhatsAppConnection,
		business=business,
		status=BusinessWhatsAppConnection.Status.ACTION_REQUIRED,
	)
	try:
		ready = retry_connection_setup(connection, request.POST.get("pin", ""))
	except MetaOnboardingError as exc:
		messages.error(request, str(exc))
	else:
		if ready:
			messages.success(request, "Le compte WhatsApp Business est connecté.")
		else:
			messages.error(request, connection.last_error)
	return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)


@login_required
@require_POST
def reply_to_business_contact(request, business_id, contact_id):
	business = _owned_business(request, business_id)
	contact = get_object_or_404(BusinessWhatsAppContact, pk=contact_id, business=business)
	try:
		send_business_reply(contact, request.POST.get("body", "").strip())
	except MetaOnboardingError as exc:
		messages.error(request, str(exc))
	else:
		messages.success(request, "Réponse envoyée à Meta.")
	return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")


@login_required
@require_POST
def update_business_contact(request, business_id, contact_id):
	business = _owned_business(request, business_id)
	if not whatsapp_entitlements(business)["can_use_crm"]:
		messages.error(request, "Le CRM WhatsApp nécessite une formule Pro active.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	contact = get_object_or_404(BusinessWhatsAppContact, pk=contact_id, business=business)
	status = request.POST.get("pipeline_status", "")
	if status not in dict(BusinessWhatsAppContact.PipelineStatus.choices):
		messages.error(request, "Choisissez un statut de suivi valide.")
		return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")

	follow_up_value = request.POST.get("next_follow_up_at", "").strip()
	follow_up = parse_date(follow_up_value) if follow_up_value else None
	if follow_up_value and follow_up is None:
		messages.error(request, "La date de relance est invalide.")
		return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")

	tags = []
	for raw_tag in request.POST.get("tags", "").split(","):
		tag = raw_tag.strip()[:30]
		if tag and tag.casefold() not in {existing.casefold() for existing in tags}:
			tags.append(tag)
		if len(tags) == 10:
			break

	contact.pipeline_status = status
	contact.notes = request.POST.get("notes", "").strip()[:5000]
	contact.tags = tags
	contact.next_follow_up_at = follow_up
	contact.save(update_fields=["pipeline_status", "notes", "tags", "next_follow_up_at", "last_activity_at"])
	messages.success(request, "Le suivi de ce contact a été mis à jour.")
	return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")


@login_required
@require_POST
def update_business_contact_consent(request, business_id, contact_id):
	business = _owned_business(request, business_id)
	if not whatsapp_entitlements(business)["can_use_crm"]:
		messages.error(request, "Le CRM WhatsApp nécessite une formule Pro active.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	contact = get_object_or_404(BusinessWhatsAppContact, pk=contact_id, business=business)
	if request.POST.get("marketing_opt_in") == "on":
		if request.POST.get("consent_confirmed") != "on":
			messages.error(request, "Confirmez que le client a donné son accord explicite.")
			return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")
		source = request.POST.get("consent_source", "").strip()[:120]
		if len(source) < 5:
			messages.error(request, "Indiquez où et quand le consentement a été recueilli.")
			return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")
		contact.marketing_opt_in = True
		contact.consent_source = source
		contact.consented_at = timezone.now()
		contact.consent_recorded_by = request.user
		contact.opted_out_at = None
		contact.save(update_fields=[
			"marketing_opt_in", "consent_source", "consented_at",
			"consent_recorded_by", "opted_out_at", "last_activity_at",
		])
		messages.success(request, "Le consentement explicite a été enregistré.")
	else:
		contact.marketing_opt_in = False
		contact.consented_at = None
		contact.consent_source = ""
		contact.consent_recorded_by = None
		contact.save(update_fields=[
			"marketing_opt_in", "consented_at", "consent_source",
			"consent_recorded_by", "last_activity_at",
		])
		cancel_scheduled_contact_messages(contact, "Le consentement marketing a été retiré.")
		messages.success(request, "Le consentement a été retiré et les relances en attente annulées.")
	return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")


@login_required
@require_GET
def business_approved_templates(request, business_id):
	business = _owned_business(request, business_id)
	if not getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False):
		return JsonResponse({"error": "Les relances WhatsApp sont désactivées par la configuration de sécurité."}, status=503)
	if not whatsapp_entitlements(business)["can_automate"]:
		return JsonResponse({"error": "Les relances automatiques nécessitent une formule Business active."}, status=403)
	try:
		templates = get_approved_template_catalog(business)
	except MetaOnboardingError as exc:
		return JsonResponse({"error": str(exc)}, status=400)
	return JsonResponse({
		"templates": [
			{
				"name": template.get("name", ""),
				"language": template.get("language", ""),
				"category": template.get("category", ""),
				"body_variables": _template_body_variable_count(template),
			}
			for template in templates
			if _template_body_supported(template)
		],
	})


def _template_body_supported(template):
	from .automations import _body_variable_count

	try:
		_body_variable_count(template)
		return True
	except MetaOnboardingError:
		return False


def _template_body_variable_count(template):
	from .automations import _body_variable_count

	try:
		return _body_variable_count(template)
	except MetaOnboardingError:
		return 0


@login_required
@require_POST
def schedule_business_template_follow_up(request, business_id, contact_id):
	business = _owned_business(request, business_id)
	if not getattr(settings, "WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED", False):
		messages.error(request, "Les relances WhatsApp sont désactivées par la configuration de sécurité.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	if not whatsapp_entitlements(business)["can_automate"]:
		messages.error(request, "Les relances automatiques nécessitent une formule Business active.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	contact = get_object_or_404(BusinessWhatsAppContact, pk=contact_id, business=business)
	if request.POST.get("confirm_send") != "on":
		messages.error(request, "Confirmez la relance planifiée avant de l’enregistrer.")
		return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")

	scheduled_for = parse_datetime(request.POST.get("scheduled_for", ""))
	if scheduled_for is not None and timezone.is_naive(scheduled_for):
		scheduled_for = timezone.make_aware(scheduled_for)
	try:
		raw_parameters = json.loads(request.POST.get("body_parameters", "[]"))
	except (TypeError, json.JSONDecodeError):
		raw_parameters = None
	if scheduled_for is None or not isinstance(raw_parameters, list):
		messages.error(request, "La date ou la liste de paramètres du modèle est invalide.")
		return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")
	try:
		schedule_template_follow_up(
			contact,
			template_name=request.POST.get("template_name", ""),
			template_language=request.POST.get("template_language", ""),
			body_parameters=raw_parameters,
			scheduled_for=scheduled_for,
			created_by=request.user,
		)
	except MetaOnboardingError as exc:
		messages.error(request, str(exc))
	else:
		messages.success(request, "La relance avec modèle approuvé est planifiée.")
	return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")


@login_required
@require_POST
def cancel_business_template_follow_up(request, business_id, contact_id, scheduled_id):
	business = _owned_business(request, business_id)
	contact = get_object_or_404(BusinessWhatsAppContact, pk=contact_id, business=business)
	scheduled = get_object_or_404(
		ScheduledBusinessWhatsAppMessage,
		pk=scheduled_id,
		contact=contact,
		status=ScheduledBusinessWhatsAppMessage.Status.SCHEDULED,
	)
	scheduled.status = ScheduledBusinessWhatsAppMessage.Status.CANCELLED
	scheduled.last_error = "Annulé par le propriétaire de la fiche."
	scheduled.save(update_fields=["status", "last_error", "updated_at"])
	messages.success(request, "La relance planifiée a été annulée.")
	return redirect(f"{reverse('whatsapp_commerce:business_dashboard', args=[business.pk])}?contact={contact.pk}")


@login_required
@require_POST
def sync_business_catalog(request, business_id):
	business = _owned_business(request, business_id)
	if not whatsapp_entitlements(business)["can_sync_catalog"]:
		messages.error(request, "La synchronisation du catalogue WhatsApp nécessite une formule Business active.")
		return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)
	connection = BusinessWhatsAppConnection.objects.filter(
		business=business,
		status=BusinessWhatsAppConnection.Status.ACTIVE,
	).first()
	if not connection:
		messages.error(request, "Connectez d’abord le compte WhatsApp Business de cette fiche.")
	elif not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", False):
		messages.error(request, "La synchronisation Meta est désactivée par la configuration de sécurité.")
	else:
		result = sync_business_catalog_items(business)
		if result["total"] == 0:
			messages.info(request, "Aucun produit actif à synchroniser.")
		else:
			messages.success(
				request,
				f"Synchronisation terminée : {result['synced']} produit(s) sur {result['total']}.",
			)
	return redirect("whatsapp_commerce:business_dashboard", business_id=business.pk)


def _product_or_404(product_id):
	product_model = apps.get_model("boutique", "Produit")
	return get_object_or_404(product_model, pk=product_id, is_published=True)


def _session_key(request):
	if not request.session.session_key:
		request.session.create()
	return request.session.session_key or ""


def _visitor_ip(request):
	candidate = request.META.get("REMOTE_ADDR", "")
	try:
		import ipaddress

		return str(ipaddress.ip_address(candidate)) if candidate else None
	except ValueError:
		return None


@require_POST
def product_view_ping(request, product_id):
	if not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", True):
		return HttpResponse(status=204)
	try:
		product = _product_or_404(product_id)
		ProductView.objects.create(
			boutique_product_id=product.pk,
			visitor_session_key=_session_key(request),
			visitor_ip=_visitor_ip(request),
		)
		return JsonResponse({"ok": True})
	except Exception:
		logger.warning("WhatsApp Commerce: vue produit non enregistrée (product_id=%s).", product_id, exc_info=True)
		return JsonResponse({"ok": False}, status=200)


@require_POST
def whatsapp_order_click(request, product_id):
	try:
		product = _product_or_404(product_id)
		if not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", True):
			return redirect(reverse("boutique:detail", kwargs={"slug": product.slug}))

		session_key = _session_key(request)
		opted_in = request.POST.get("whatsapp_opt_in") == "on"
		phone = normalize_phone(request.POST.get("visitor_phone", "")) if opted_in else ""
		view = ProductView.objects.filter(
			boutique_product_id=product.pk,
			visitor_session_key=session_key,
			converted=False,
		).order_by("-viewed_at").first()
		if view is None:
			view = ProductView(
				boutique_product_id=product.pk,
				visitor_session_key=session_key,
				visitor_ip=_visitor_ip(request),
			)
		view.visitor_phone = phone or None
		view.whatsapp_opt_in = bool(phone and opted_in)
		view.save()

		order_url = get_whatsapp_order_url(product)
		if not order_url:
			logger.warning("WhatsApp Commerce: numéro officiel ou URL produit absent (product_id=%s).", product.pk)
			return redirect(reverse("boutique:detail", kwargs={"slug": product.slug}))
		return redirect(order_url)
	except Exception:
		logger.warning("WhatsApp Commerce: redirection de commande indisponible (product_id=%s).", product_id, exc_info=True)
		try:
			product = _product_or_404(product_id)
			return redirect(reverse("boutique:detail", kwargs={"slug": product.slug}))
		except Exception:
			return redirect("/boutique/")
