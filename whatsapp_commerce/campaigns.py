import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from whatsapp_agent.meta_templates import message_parameters
from whatsapp_agent.models import MessageEnvoi

from .inbox import normalize_phone
from .models import BusinessWhatsAppConnection, BusinessWhatsAppMessage
from .onboarding import MetaOnboardingError, _request_meta


def _connection_for_business(business):
    connection = BusinessWhatsAppConnection.objects.filter(
        business=business,
        status=BusinessWhatsAppConnection.Status.ACTIVE,
        phone_registered=True,
        webhook_subscribed=True,
    ).first()
    if connection is None:
        raise MetaOnboardingError("Le compte WhatsApp Business n’est pas entièrement connecté.")
    return connection


def _template_catalog(connection):
    cache_key = f"wa-business-campaign-templates:{connection.waba_id}"
    catalog = cache.get(cache_key)
    if catalog is not None:
        return catalog

    response = _request_meta(
        "GET",
        f"{connection.waba_id}/message_templates",
        token=connection.get_access_token(),
        params={"fields": "name,status,language,category,components", "limit": 100},
    )
    templates = response.get("data", [])
    if not isinstance(templates, list):
        raise MetaOnboardingError("Meta a retourné un catalogue de modèles invalide.")

    from .automations import _body_variable_count

    catalog = []
    for template in templates:
        if not isinstance(template, dict) or template.get("status") != "APPROVED":
            continue
        category = str(template.get("category", "")).upper()
        body = ""
        try:
            parameter_count = _body_variable_count(template)
            body = next(
                (
                    str(component.get("text", ""))
                    for component in template.get("components", [])
                    if isinstance(component, dict)
                    and str(component.get("type", "")).upper() == "BODY"
                ),
                "",
            )
            supported = category == "MARKETING"
            reason = "" if supported else "Les campagnes PME exigent un modèle de catégorie MARKETING."
        except MetaOnboardingError as exc:
            parameter_count = 0
            supported = False
            reason = str(exc)
        catalog.append(
            {
                "key": f'{template.get("name", "")}|{template.get("language", "")}',
                "name": str(template.get("name", "")),
                "language": str(template.get("language", "")),
                "category": category,
                "body": body,
                "parameter_count": parameter_count,
                "supported": supported,
                "reason": reason,
            }
        )
    cache.set(cache_key, catalog, 120)
    return catalog


def business_campaign_template_catalog(business):
    connection = _connection_for_business(business)
    if not connection.get_access_token():
        raise MetaOnboardingError("Le jeton WhatsApp Business est indisponible.")
    return _template_catalog(connection)


def validate_business_campaign_template(business, name, language, params):
    connection = _connection_for_business(business)
    if not connection.get_access_token():
        raise MetaOnboardingError("Le jeton WhatsApp Business est indisponible.")
    key = f"{name}|{language}"
    template = next((item for item in _template_catalog(connection) if item["key"] == key), None)
    if not template or not template["supported"]:
        reason = template["reason"] if template else "Ce modèle n’est pas approuvé pour le WABA de cette entreprise."
        raise MetaOnboardingError(reason)
    if len(params) != template["parameter_count"]:
        raise MetaOnboardingError(
            f"Ce modèle attend {template['parameter_count']} variable(s) de corps."
        )
    return connection, template


def send_business_campaign_message(message):
    contact = message.business_contact
    campaign = message.campagne
    if (
        contact is None
        or contact.business_id != campaign.business_id
        or contact.consent_marketing is not True
        or contact.marketing_opt_in is not True
        or contact.opted_out_at is not None
    ):
        return {
            "success": False,
            "message_id": "",
            "erreur": "Consentement marketing absent ou retiré avant l'envoi.",
        }

    connection = _connection_for_business(campaign.business)
    if getattr(settings, "WHATSAPP_DRY_RUN", True):
        return {
            "success": True,
            "message_id": f"dryrun-business-{message.pk}-{int(time.time() * 1000)}",
            "erreur": "Simulation : aucun appel Meta effectué.",
        }

    token = connection.get_access_token()
    if not token:
        return {"success": False, "message_id": "", "erreur": "Le jeton WhatsApp Business est indisponible."}

    if campaign.template_meta_name:
        _connection, template = validate_business_campaign_template(
            campaign.business,
            campaign.template_meta_name,
            campaign.template_meta_language,
            campaign.template_meta_params,
        )
        params = message_parameters(campaign, message)
        components = []
        if params:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": value} for value in params],
                }
            )
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalize_phone(contact.phone).lstrip("+"),
            "type": "template",
            "template": {
                "name": template["name"],
                "language": {"code": template["language"]},
                **({"components": components} if components else {}),
            },
        }
        message_type = "template"
        message_body = template["body"]
    else:
        if not contact.last_inbound_at or contact.last_inbound_at < timezone.now() - timedelta(hours=24):
            return {
                "success": False,
                "message_id": "",
                "erreur": "Hors de la fenêtre de 24 h : sélectionne un modèle MARKETING approuvé par Meta pour ce WABA.",
            }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalize_phone(contact.phone).lstrip("+"),
            "type": "text",
            "text": {"body": message.message_final, "preview_url": False},
        }
        message_type = "text"
        message_body = message.message_final

    response = _request_meta(
        "POST",
        f"{connection.phone_number_id}/messages",
        token=token,
        payload=payload,
    )
    wa_messages = response.get("messages", [])
    wa_message_id = str(wa_messages[0].get("id", "")) if wa_messages else ""
    if not wa_message_id:
        return {"success": False, "message_id": "", "erreur": "Meta n’a pas confirmé la prise en charge du message."}

    BusinessWhatsAppMessage.objects.create(
        contact=contact,
        wa_message_id=wa_message_id,
        direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
        message_type=message_type,
        body=message_body,
        status="sent",
        meta_timestamp=timezone.now(),
    )
    return {"success": True, "message_id": wa_message_id, "erreur": ""}


def _vocal_campaign_script(business, product, lang):
    language = (lang or business.language or "fr").casefold()
    if language not in dict(business.Language.choices):
        raise ValueError("Langue vocale non prise en charge.")
    name = product.title
    price = product.price_label or (
        f"{product.prix_gros_xaf}F" if product.prix_gros_xaf else "prix disponible sur demande"
    )
    stock = product.stock_quantity
    if language == "fr":
        return f"{business.name}: {name} à {price}, {stock} unités disponibles." if stock is not None else f"{business.name}: {name} à {price}."
    if language == "en":
        return f"{business.name}: {name} at {price}, {stock} units available." if stock is not None else f"{business.name}: {name} at {price}."
    if language == "pidgin":
        return f"My broda, {name} don land for {business.district or business.city}, na {price}, e get {stock} units. You wan order?" if stock is not None else f"My broda, {name} don land, na {price}. You wan order?"

    # Ewondo and Bassa copy is generated on demand; keep the exact product,
    # price and stock values in the prompt and reject output that drops them.
    from e_shelle_ai.services.openai_service import EshelleAIService

    ai = EshelleAIService()
    if not ai.client:
        raise RuntimeError("La traduction vocale Ewondo/Bassa nécessite le service IA configuré.")
    response = ai.client.chat.completions.create(
        model=ai.chat_model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "Translate the short sales message into the requested language. Do not invent facts; preserve the product, price, and quantity exactly. Return only the spoken sentence.",
            },
            {
                "role": "user",
                "content": f"Language: {language}. Business: {business.name}. Product: {name}. Price: {price}. Stock: {stock if stock is not None else 'not specified'}.",
            },
        ],
    )
    translated = response.choices[0].message.content.strip()
    if str(price) not in translated or (stock is not None and str(stock) not in translated):
        raise RuntimeError("La traduction vocale n’a pas conservé les données produit requises.")
    return translated


def _generate_business_vocal(business, product, language):
    if not business.owner_id:
        raise ValueError("Le profil Business doit avoir un propriétaire pour créer une voix-off.")
    from audio_studio.models import VoiceOverJob

    job = VoiceOverJob.objects.create(
        user=business.owner,
        title=f"WhatsApp {product.title}"[:160],
        script=_vocal_campaign_script(business, product, language),
        mode=VoiceOverJob.Mode.LOCAL,
        openai_voice=VoiceOverJob.OpenAIVoice.NOVA,
    )
    try:
        from audio_studio.services import generate_voiceover_audio

        generate_voiceover_audio(job)
    except Exception as exc:
        job.status = VoiceOverJob.Status.FAILED
        job.error_message = "La génération de la voix-off a échoué."
        job.save(update_fields=["status", "error_message"])
        raise RuntimeError("Impossible de générer le fichier vocal de campagne.") from exc
    if job.status != VoiceOverJob.Status.DONE or not job.audio_file:
        raise RuntimeError("La génération vocale n’a produit aucun fichier audio.")
    return job


def send_vocal_campaign(business, contacts, product, lang):
    """Generate one product voice note and send it to opted-in contacts of one business."""
    language = (lang or business.language or "fr").casefold()
    connection = _connection_for_business(business)
    token = connection.get_access_token()
    if not token and not getattr(settings, "WHATSAPP_DRY_RUN", True):
        raise MetaOnboardingError("Le jeton WhatsApp Business est indisponible.")
    job = _generate_business_vocal(business, product, language)
    audio_url = job.audio_file.url
    results = {"sent": 0, "skipped": 0, "failed": 0, "language": language}
    for contact in contacts:
        if (
            contact.business_id != business.pk
            or contact.consent_marketing is not True
            or contact.marketing_opt_in is not True
            or contact.opted_out_at is not None
        ):
            results["skipped"] += 1
            continue
        if getattr(settings, "WHATSAPP_DRY_RUN", True):
            results["sent"] += 1
            continue
        try:
            response = _request_meta(
                "POST",
                f"{connection.phone_number_id}/messages",
                token=token,
                payload={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": normalize_phone(contact.phone).lstrip("+"),
                    "type": "audio",
                    "audio": {"link": audio_url},
                },
            )
            messages = response.get("messages", [])
            message_id = str(messages[0].get("id", "")) if messages else ""
            if not message_id:
                results["failed"] += 1
                continue
            BusinessWhatsAppMessage.objects.create(
                contact=contact,
                wa_message_id=message_id,
                direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
                message_type="audio",
                language=language,
                body=f"{product.title} — {product.price_label}",
                status="sent",
                meta_timestamp=timezone.now(),
            )
            results["sent"] += 1
        except Exception:
            results["failed"] += 1
    return results


def lancer_njangi_achat(njangi_id):
    """Invite opted-in quincaillerie contacts in Akwa to an open group purchase."""
    from django.db import transaction
    from django.db.models import Q
    from njangi.models import NjangiAchatGroupe, NjangiAchatParticipation

    with transaction.atomic():
        group = NjangiAchatGroupe.objects.select_for_update().select_related("product").get(pk=njangi_id)
        if group.status != NjangiAchatGroupe.Status.OPEN or group.date_cloture <= timezone.now():
            return {"sent": 0, "skipped": 0, "failed": 0, "reason": "closed"}
        remaining = max(0, group.quantite_cible - group.quantite_actuelle)
        proposed_quantity = min(group.quantite_proposee_par_boutique, remaining)
        if proposed_quantity <= 0:
            return {"sent": 0, "skipped": 0, "failed": 0, "reason": "target_reached"}
        businesses = group.product.business.__class__.objects.filter(
            module="quincaillerie",
        ).filter(Q(city__icontains="Akwa") | Q(district__icontains="Akwa"))
        sent = skipped = failed = 0
        for business in businesses:
            connection = BusinessWhatsAppConnection.objects.filter(
                business=business,
                status=BusinessWhatsAppConnection.Status.ACTIVE,
                phone_registered=True,
                webhook_subscribed=True,
            ).first()
            if connection is None:
                skipped += 1
                continue
            contacts = business.whatsapp_contacts.filter(
                consent_marketing=True,
                marketing_opt_in=True,
                opted_out_at__isnull=True,
            )
            if not contacts.exists():
                skipped += 1
                continue
            participation, created = NjangiAchatParticipation.objects.get_or_create(
                achat_groupe=group,
                business=business,
                defaults={"quantity": proposed_quantity, "status": NjangiAchatParticipation.Status.INVITED},
            )
            if not created and participation.status == NjangiAchatParticipation.Status.ACCEPTED:
                skipped += 1
                continue
            days_left = max(0, (group.date_cloture - timezone.now()).days)
            savings = group.economie_par_boutique(proposed_quantity)
            body = (
                f"Njangi {group.product.title}: {group.quantite_actuelle}/{group.quantite_cible} unités prises. "
                f"Il manque {remaining}. Tu prends {proposed_quantity} à {group.prix_njangi}F au lieu de "
                f"{group.prix_normal}F ? Économie {savings}F. Réponds OUI. Il reste {days_left}j."
            )
            for contact in contacts:
                if not contact.last_inbound_at or contact.last_inbound_at < timezone.now() - timedelta(hours=24):
                    skipped += 1
                    continue
                if getattr(settings, "WHATSAPP_DRY_RUN", True):
                    sent += 1
                    continue
                token = connection.get_access_token()
                if not token:
                    failed += 1
                    continue
                try:
                    response = _request_meta(
                        "POST",
                        f"{connection.phone_number_id}/messages",
                        token=token,
                        payload={
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": normalize_phone(contact.phone).lstrip("+"),
                            "type": "text",
                            "text": {"body": body, "preview_url": False},
                        },
                    )
                    items = response.get("messages", [])
                    message_id = str(items[0].get("id", "")) if items else ""
                    if not message_id:
                        failed += 1
                        continue
                    BusinessWhatsAppMessage.objects.create(
                        contact=contact,
                        wa_message_id=message_id,
                        direction=BusinessWhatsAppMessage.Direction.OUTBOUND,
                        message_type="text",
                        language=business.language,
                        body=body,
                        status="sent",
                        meta_timestamp=timezone.now(),
                    )
                    sent += 1
                except Exception:
                    failed += 1
        return {"sent": sent, "skipped": skipped, "failed": failed}


def accept_njangi_invitation(contact, body):
    """Apply an explicit OUI reply to the latest open group invite for this business."""
    import re

    from django.db import transaction
    from njangi.models import NjangiAchatGroupe, NjangiAchatParticipation

    match = re.fullmatch(r"oui(?:\s+(\d+))?", (body or "").strip(), flags=re.IGNORECASE)
    if not match or contact.opted_out_at or contact.consent_marketing is not True or contact.marketing_opt_in is not True:
        return None
    with transaction.atomic():
        participation = (
            NjangiAchatParticipation.objects.select_for_update()
            .select_related("achat_groupe")
            .filter(
                business=contact.business,
                status=NjangiAchatParticipation.Status.INVITED,
                achat_groupe__status=NjangiAchatGroupe.Status.OPEN,
                achat_groupe__date_cloture__gt=timezone.now(),
            )
            .order_by("achat_groupe__date_cloture", "pk")
            .first()
        )
        if participation is None:
            return None
        group = NjangiAchatGroupe.objects.select_for_update().get(pk=participation.achat_groupe_id)
        amount = int(match.group(1) or participation.quantity or group.quantite_proposee_par_boutique)
        remaining = max(0, group.quantite_cible - group.quantite_actuelle)
        amount = min(amount, remaining)
        if amount <= 0:
            return None
        participation.quantity = amount
        participation.status = NjangiAchatParticipation.Status.ACCEPTED
        participation.accepted_at = timezone.now()
        participation.save(update_fields=["quantity", "status", "accepted_at"])
        group.businesses_participants.add(participation.business)
        group.quantite_actuelle += amount
        if group.quantite_actuelle >= group.quantite_cible:
            group.quantite_actuelle = group.quantite_cible
            group.status = NjangiAchatGroupe.Status.REACHED
        group.save(update_fields=["quantite_actuelle", "status", "updated_at"])
        return {"group": group, "quantity": amount, "reached": group.status == NjangiAchatGroupe.Status.REACHED}
