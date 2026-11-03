import csv
import io

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from business.models import BusinessProfile
from business.services import get_audience_for_campaign
from whatsapp_agent.forms import TemplateSelectionForm
from whatsapp_agent.models import Campagne, MessageEnvoi
from whatsapp_agent.tasks import lancer_campagne_direct, lancer_campagne_task, recalculer_stats_campagne

from .campaigns import business_campaign_template_catalog, validate_business_campaign_template
from .entitlements import whatsapp_entitlements
from .models import BusinessWhatsAppConnection, BusinessWhatsAppContact
from .onboarding import MetaOnboardingError
from .services import normalize_phone

MAX_CAMPAIGN_RECIPIENTS = 250
MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_IMPORT_ROWS = 5000


def _owned_business(request, business_id):
    return get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)


def _active_connection(business):
    return BusinessWhatsAppConnection.objects.filter(
        business=business,
        status=BusinessWhatsAppConnection.Status.ACTIVE,
        phone_registered=True,
        webhook_subscribed=True,
    ).first()


def _campaign_context(business, connection):
    campaigns = Campagne.objects.filter(business=business).order_by("-cree_le")
    return {
        "business": business,
        "connection": connection,
        "campaigns": campaigns,
        "eligible_contacts": get_audience_for_campaign(business).count(),
        "total_contacts": BusinessWhatsAppContact.objects.filter(business=business).count(),
        "campaign_limit": MAX_CAMPAIGN_RECIPIENTS,
        "entitlements": whatsapp_entitlements(business),
        "whatsapp_enabled": bool(getattr(settings, "WHATSAPP_COMMERCE_ENABLED", False)),
    }


@login_required
@require_GET
def campaigns_home(request):
    businesses = BusinessProfile.objects.filter(owner=request.user).order_by("name")
    rows = []
    for business in businesses:
        rows.append(
            {
                "business": business,
                "entitlements": whatsapp_entitlements(business),
                "connection": _active_connection(business),
                "campaign_count": Campagne.objects.filter(business=business).count(),
                "eligible_contacts": get_audience_for_campaign(business).count(),
            }
        )
    return render(request, "whatsapp_commerce/business_campaigns.html", {"business_rows": rows})


@login_required
@require_GET
def business_campaigns(request, business_id):
    business = _owned_business(request, business_id)
    connection = _active_connection(business)
    context = _campaign_context(business, connection)
    context.update({"templates": [], "template_error": ""})
    if (
        connection
        and context["entitlements"]["can_use_crm"]
        and context["whatsapp_enabled"]
    ):
        try:
            context["templates"] = [
                template for template in business_campaign_template_catalog(business)
                if template["supported"]
            ]
        except MetaOnboardingError as exc:
            context["template_error"] = str(exc)
    return render(request, "whatsapp_commerce/business_campaigns.html", context)


def _import_contacts(business, user, uploaded_file, consent_source):
    if uploaded_file.size > MAX_IMPORT_BYTES:
        raise ValueError("Le fichier CSV ne peut pas dépasser 2 Mo.")
    try:
        content = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Le CSV doit être encodé en UTF-8.") from exc

    reader = csv.DictReader(io.StringIO(content))
    headers = {
        (header or "").strip().casefold(): header
        for header in (reader.fieldnames or [])
    }
    phone_column = next(
        (headers[name] for name in ("phone", "numero", "numéro", "whatsapp", "telephone", "téléphone") if name in headers),
        None,
    )
    name_column = next(
        (headers[name] for name in ("name", "nom", "display_name") if name in headers),
        None,
    )
    if not phone_column:
        raise ValueError("Le CSV doit contenir une colonne phone (ou numéro/whatsapp).")

    imported = skipped_invalid = skipped_opted_out = 0
    seen = set()
    now = timezone.now()
    with transaction.atomic():
        for row_number, row in enumerate(reader, start=2):
            if row_number > MAX_IMPORT_ROWS + 1:
                raise ValueError(f"Le fichier ne peut pas dépasser {MAX_IMPORT_ROWS} lignes.")
            phone = normalize_phone(row.get(phone_column, ""))
            if not phone or phone in seen:
                skipped_invalid += 1
                continue
            seen.add(phone)
            contact = BusinessWhatsAppContact.objects.get_or_create(
                business=business,
                phone=phone,
            )[0]
            if contact.opted_out_at:
                skipped_opted_out += 1
                continue
            contact.display_name = (
                (row.get(name_column) or "").strip()[:180] if name_column else contact.display_name
            )
            contact.marketing_opt_in = True
            contact.consent_marketing = True
            contact.consent_source = consent_source
            contact.consented_at = now
            contact.consent_recorded_by = user
            contact.save(
                update_fields=[
                    "display_name",
                    "marketing_opt_in",
                    "consent_marketing",
                    "consent_source",
                    "consented_at",
                    "consent_recorded_by",
                ]
            )
            imported += 1
    return imported, skipped_invalid, skipped_opted_out


@login_required
@require_POST
def import_business_campaign_contacts(request, business_id):
    business = _owned_business(request, business_id)
    if not whatsapp_entitlements(business)["can_use_crm"]:
        messages.error(request, "L’import de contacts nécessite un abonnement Pro, Business ou Premium actif.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)
    uploaded_file = request.FILES.get("contacts_file")
    consent_source = request.POST.get("consent_source", "").strip()
    if not uploaded_file or request.POST.get("consent_attestation") != "on" or not consent_source:
        messages.error(request, "Ajoutez un CSV, indiquez la source du consentement et confirmez votre attestation.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)
    if len(consent_source) > 120:
        messages.error(request, "La source du consentement est limitée à 120 caractères.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)
    try:
        imported, skipped_invalid, skipped_opted_out = _import_contacts(
            business, request.user, uploaded_file, consent_source
        )
    except (ValueError, csv.Error) as exc:
        messages.error(request, str(exc))
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)
    messages.success(
        request,
        f"{imported} contact(s) importé(s) avec consentement enregistré ; "
        f"{skipped_invalid} ligne(s) invalide(s)/dupliquée(s), "
        f"{skipped_opted_out} désinscrit(s) ignoré(s).",
    )
    return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)


@login_required
@require_POST
def create_business_campaign(request, business_id):
    business = _owned_business(request, business_id)
    if not whatsapp_entitlements(business)["can_use_crm"]:
        messages.error(request, "Les campagnes nécessitent un abonnement Pro, Business ou Premium actif.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)
    if not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", False) or not _active_connection(business):
        messages.error(request, "Reliez d’abord un WABA actif et vérifiez que le service WhatsApp est activé.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)

    selection = TemplateSelectionForm(request.POST, business=business)
    name = request.POST.get("nom", "").strip()
    consent_acknowledged = request.POST.get("consent_attestation") == "on"
    if not name or len(name) > 200:
        messages.error(request, "Le nom de la campagne est obligatoire (200 caractères maximum).")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)
    if not consent_acknowledged:
        messages.error(request, "Confirmez que les destinataires ont accepté de recevoir vos offres sur WhatsApp.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)
    if not selection.is_valid() or not selection.cleaned_data.get("selected"):
        errors = " ".join(
            str(error)
            for field_errors in selection.errors.values()
            for error in field_errors
        )
        messages.error(request, errors or "Sélectionnez un modèle MARKETING approuvé par Meta.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)

    eligible = get_audience_for_campaign(business)
    recipient_count = eligible.count()
    if recipient_count == 0:
        messages.error(request, "Aucun contact de cette entreprise n’a un consentement marketing actif.")
        return redirect("whatsapp_commerce:business_campaigns", business_id=business.pk)

    selected = selection.cleaned_data["selected"]
    params = selection.cleaned_data.get("meta_params") or []
    campaign = Campagne(
        nom=name,
        description=request.POST.get("description", "").strip()[:2000],
        business=business,
        message_template=selected["body"],
        consent_type=Campagne.CONSENT_MARKETING,
        template_meta_name=selected["name"],
        template_meta_language=selected["language"],
        template_meta_params=params,
        template_meta_preview=selected["body"],
        statut=Campagne.STATUT_VALIDEE,
        cree_par=request.user,
    )
    with transaction.atomic():
        campaign.save()
        batch = []
        for contact in eligible.order_by("pk")[:MAX_CAMPAIGN_RECIPIENTS]:
            first_name = (contact.display_name or "Client").split()[0]
            preview = selected["body"]
            for index, value in enumerate(params, start=1):
                preview = preview.replace(
                    "{{" + str(index) + "}}",
                    value.replace("{{prenom}}", first_name),
                )
            batch.append(
                MessageEnvoi(
                    campagne=campaign,
                    business_contact=contact,
                    destinataire_nom=contact.display_name or contact.phone,
                    numero_whatsapp=contact.phone,
                    message_final=preview,
                )
            )
        MessageEnvoi.objects.bulk_create(batch, batch_size=MAX_CAMPAIGN_RECIPIENTS)
        recalculer_stats_campagne(campaign)
    if recipient_count > MAX_CAMPAIGN_RECIPIENTS:
        messages.warning(
            request,
            f"La campagne est limitée aux {MAX_CAMPAIGN_RECIPIENTS} premiers contacts consentants.",
        )
    else:
        messages.success(request, "Campagne prête. Vérifiez le modèle et les destinataires avant le lancement.")
    return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)


@login_required
@require_GET
def business_campaign_detail(request, business_id, campaign_id):
    business = _owned_business(request, business_id)
    campaign = get_object_or_404(Campagne, pk=campaign_id, business=business)
    recalculer_stats_campagne(campaign)
    page_obj = Paginator(
        campaign.messages.select_related("business_contact").order_by("pk"), 50
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "whatsapp_commerce/business_campaigns.html",
        {
            **_campaign_context(business, _active_connection(business)),
            "campaign_detail": campaign,
            "page_obj": page_obj,
            "campaign_limit": MAX_CAMPAIGN_RECIPIENTS,
        },
    )


@login_required
@require_POST
def launch_business_campaign(request, business_id, campaign_id):
    business = _owned_business(request, business_id)
    campaign = get_object_or_404(Campagne, pk=campaign_id, business=business)
    if not whatsapp_entitlements(business)["can_use_crm"]:
        messages.error(request, "L’abonnement de cette entreprise ne permet plus de lancer des campagnes.")
        return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)
    if not getattr(settings, "WHATSAPP_COMMERCE_ENABLED", False) or not _active_connection(business):
        messages.error(request, "La connexion WABA ou le service WhatsApp n’est plus actif.")
        return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)
    if campaign.statut != Campagne.STATUT_VALIDEE or request.POST.get("confirm_launch") != "on":
        messages.error(request, "Confirmez le lancement d’une campagne prête.")
        return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)
    try:
        validate_business_campaign_template(
            business,
            campaign.template_meta_name,
            campaign.template_meta_language,
            campaign.template_meta_params,
        )
    except MetaOnboardingError as exc:
        messages.error(request, str(exc))
        return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)

    eligible_ids = get_audience_for_campaign(business).values_list("pk", flat=True)
    campaign.messages.filter(
        business_contact__isnull=False,
        statut=MessageEnvoi.STATUT_EN_ATTENTE,
    ).exclude(business_contact_id__in=eligible_ids).update(
        statut=MessageEnvoi.STATUT_ECHEC,
        erreur="Consentement marketing absent ou retiré avant l'envoi.",
    )
    if not campaign.messages.filter(statut=MessageEnvoi.STATUT_EN_ATTENTE).exists():
        messages.error(request, "Aucun destinataire consentant ne reste à envoyer.")
        return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)

    claimed = Campagne.objects.filter(
        pk=campaign.pk,
        business=business,
        statut=Campagne.STATUT_VALIDEE,
        template_meta_name=campaign.template_meta_name,
        template_meta_language=campaign.template_meta_language,
        template_meta_params=campaign.template_meta_params,
    ).update(statut=Campagne.STATUT_EN_COURS)
    if not claimed:
        messages.error(request, "Cette campagne a déjà été modifiée ou lancée. Actualisez la page.")
        return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)
    if settings.WHATSAPP_DRY_RUN:
        lancer_campagne_direct(campaign.pk)
        messages.success(request, "Simulation terminée : aucun message n’a été envoyé à Meta.")
    else:
        try:
            lancer_campagne_task.delay(campaign.pk)
            messages.success(request, "Campagne programmée. Les statuts apparaîtront ici au fur et à mesure.")
        except Exception as exc:
            Campagne.objects.filter(
                pk=campaign.pk,
                statut=Campagne.STATUT_EN_COURS,
                lance_le__isnull=True,
            ).update(statut=Campagne.STATUT_VALIDEE)
            messages.error(request, f"Impossible de programmer la campagne : {exc}")
    return redirect("whatsapp_commerce:business_campaign_detail", business_id=business.pk, campaign_id=campaign.pk)
