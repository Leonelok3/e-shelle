import csv
import hashlib
import hmac
import json
import mimetypes
import os
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError, SuspiciousFileOperation
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import CampagneForm, TemplateSelectionForm
from .calling import WhatsAppCallingError, get_call_permission, initiate_call, post_call_action, request_call_permission
from .meta_templates import TemplateError, approved_templates, validate_selection, message_parameters, template_preview
from .models import Campagne, ContactWhatsApp, ConversationWhatsApp, MessageEnvoi, MessageWhatsApp, WhatsAppCall, WhatsAppTestSend
from .services import AI_PRESETS, WhatsAppService
from .tasks import lancer_campagne_direct, lancer_campagne_task, recalculer_stats_campagne


def staff_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


@staff_required
def api_templates_meta(request):
    try:
        return JsonResponse({'templates': approved_templates()})
    except TemplateError as exc:
        return JsonResponse({'templates': [], 'error': str(exc)}, status=503)


@staff_required
@require_POST
def selectionner_modele(request, pk):
    selection = TemplateSelectionForm(request.POST)
    if not selection.is_valid():
        messages.error(request, ' '.join(str(e) for errors in selection.errors.values() for e in errors))
        return redirect('whatsapp_agent:wa_detail', pk=pk)
    with transaction.atomic():
        campaign = get_object_or_404(Campagne.objects.select_for_update(), pk=pk)
        if campaign.statut not in (Campagne.STATUT_BROUILLON, Campagne.STATUT_VALIDEE) or campaign.messages.exclude(statut=MessageEnvoi.STATUT_EN_ATTENTE).exists():
            messages.error(request, 'Le modele ne peut plus etre change apres le debut des envois. Duplique la campagne pour un nouvel envoi.')
        else:
            selection.apply(campaign)
            campaign.save(update_fields=['template_meta_name', 'template_meta_language', 'template_meta_params', 'template_meta_preview'])
            messages.success(request, 'Modele enregistre pour le test et toute la campagne.')
    return redirect('whatsapp_agent:wa_detail', pk=pk)


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def _parse_liste_numeros(raw_text):
    """Extrait des numeros WhatsApp depuis une liste collee librement."""

    numeros = []
    seen = set()
    chunks = re.split(r"[\n,;]+", raw_text or "")
    for chunk in chunks:
        item = chunk.strip()
        if not item:
            continue
        has_plus = item.startswith("+")
        digits = re.sub(r"\D", "", item)
        if not digits:
            continue
        if has_plus:
            numero = f"+{digits}"
        elif digits.startswith("00"):
            numero = f"+{digits[2:]}"
        elif digits.startswith("237"):
            numero = f"+{digits}"
        elif len(digits) >= 8:
            numero = f"+237{digits}"
        else:
            continue
        if numero not in seen:
            seen.add(numero)
            numeros.append(numero)
    return numeros


def _creer_messages_campagne(campagne):
    """Prepare les lignes MessageEnvoi selon les filtres de la campagne."""

    campagne.messages.all().delete()
    template_brut = campagne.message_template or ""
    # Support du multi-variations si le texte contient le separateur ---VARIATION---
    variantes = [v.strip() for v in template_brut.split("---VARIATION---") if v.strip()]
    if not variantes:
        variantes = [template_brut]

    contacts_whatsapp = campagne.destinataires_contacts.filter(
        consentement_confirme=True,
        desinscrit=False,
    ).order_by("nom", "numero")
    if contacts_whatsapp.exists():
        batch = []
        for idx, contact in enumerate(contacts_whatsapp):
            tpl_choisi = variantes[idx % len(variantes)]
            msg_final = WhatsAppService.personnaliser_message(tpl_choisi, contact=contact)
            batch.append(
                MessageEnvoi(
                    campagne=campagne,
                    destinataire_nom=contact.nom or f"Contact WhatsApp {contact.numero}",
                    numero_whatsapp=contact.numero,
                    message_final=msg_final,
                )
            )
        MessageEnvoi.objects.bulk_create(batch, batch_size=500)
        recalculer_stats_campagne(campagne)
        return

    contacts = WhatsAppService.recuperer_contacts(
        campagne.filtre_role,
        campagne.filtre_ville,
        campagne.filtre_date_inscription_depuis,
    )
    batch = []
    idx = 0
    for user in contacts:
        if WhatsAppService.deja_contacte(user.whatsapp):
            continue
        tpl_choisi = variantes[idx % len(variantes)]
        msg_final = WhatsAppService.personnaliser_message(tpl_choisi, user=user)
        batch.append(
            MessageEnvoi(
                campagne=campagne,
                user=user,
                numero_whatsapp=user.whatsapp,
                message_final=msg_final,
            )
        )
        idx += 1
    MessageEnvoi.objects.bulk_create(batch, batch_size=500)
    recalculer_stats_campagne(campagne)


def _personnaliser_message_contact(template, contact):
    """Personnalise un message pour un contact WhatsApp importe avec fallback intelligent et Spintax."""
    return WhatsAppService.personnaliser_message(template, contact=contact)


@staff_required
def contacts_whatsapp(request):
    """Carnet global des contacts WhatsApp importes."""

    q = request.GET.get("q", "").strip()
    ville = request.GET.get("ville", "").strip()
    groupe = request.GET.get("groupe", "").strip()
    source = request.GET.get("source", "").strip()

    contacts = ContactWhatsApp.objects.select_related("importe_par").order_by("-cree_le")
    if q:
        contacts = contacts.filter(
            Q(nom__icontains=q)
            | Q(numero__icontains=q)
            | Q(note__icontains=q)
            | Q(groupe__icontains=q)
        )
    if ville:
        contacts = contacts.filter(ville__icontains=ville)
    if groupe:
        contacts = contacts.filter(groupe__icontains=groupe)
    if source:
        contacts = contacts.filter(source=source)

    paginator = Paginator(contacts, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    total_contacts = ContactWhatsApp.objects.count()
    total_autorises = ContactWhatsApp.objects.filter(consentement_confirme=True, desinscrit=False).count()

    return render(
        request,
        "whatsapp_agent/contacts.html",
        {
            "page_obj": page_obj,
            "q": q,
            "ville": ville,
            "groupe": groupe,
            "source": source,
            "sources": ContactWhatsApp.SOURCES,
            "total_contacts": total_contacts,
            "total_autorises": total_autorises,
            "total_filtres": contacts.count(),
            "total_campagnes": Campagne.objects.count(),
        },
    )


@staff_required
@require_POST
def creer_campagne_contacts(request):
    """Cree une campagne depuis une selection manuelle ou tous les contacts filtres."""

    select_all_filtered = request.POST.get("select_all_filtered") in ("1", "true", "on")
    if select_all_filtered:
        q = request.POST.get("filter_q", "").strip()
        ville = request.POST.get("filter_ville", "").strip()
        groupe = request.POST.get("filter_groupe", "").strip()
        source = request.POST.get("filter_source", "").strip()

        contacts = ContactWhatsApp.objects.filter(
            consentement_confirme=True,
            desinscrit=False,
        )
        if q:
            contacts = contacts.filter(
                Q(nom__icontains=q)
                | Q(numero__icontains=q)
                | Q(note__icontains=q)
                | Q(groupe__icontains=q)
            )
        if ville:
            contacts = contacts.filter(ville__icontains=ville)
        if groupe:
            contacts = contacts.filter(groupe__icontains=groupe)
        if source:
            contacts = contacts.filter(source=source)
    else:
        contact_ids = request.POST.getlist("contacts")
        contacts = ContactWhatsApp.objects.filter(
            id__in=contact_ids,
            consentement_confirme=True,
            desinscrit=False,
        )

    if not contacts.exists():
        messages.warning(request, "Selectionne au moins un contact autorise avant de creer une campagne.")
        return redirect("whatsapp_agent:wa_contacts")

    nom = request.POST.get("nom", "").strip() or f"Campagne WhatsApp selection {timezone.now():%d/%m/%Y}"
    message_template = request.POST.get("message_template", "").strip()
    if not message_template:
        messages.warning(request, "Ajoute un message avant de creer la campagne.")
        return redirect("whatsapp_agent:wa_contacts")

    campagne = Campagne.objects.create(
        nom=nom,
        description="Campagne creee depuis le carnet global des contacts WhatsApp.",
        message_template=message_template,
        statut=Campagne.STATUT_VALIDEE,
        filtre_role="selection_contacts",
        cree_par=request.user,
    )
    campagne.destinataires_contacts.set(contacts)
    _creer_messages_campagne(campagne)
    messages.success(
        request,
        f"Campagne creee avec {campagne.total_destinataires} contact(s) selectionne(s). Verifie avant lancement.",
    )
    return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)


@staff_required
def dashboard_campagnes(request):
    """Liste des campagnes WhatsApp avec statistiques globales."""

    statut = request.GET.get("statut", "")
    campagnes = Campagne.objects.select_related("cree_par").order_by("-cree_le")
    if statut:
        campagnes = campagnes.filter(statut=statut)

    aggregate = Campagne.objects.aggregate(
        total=Count("id"),
        envoyes=Sum("total_envoyes"),
        livres=Sum("total_livres"),
        echecs=Sum("total_echecs"),
    )
    total_envoyes = aggregate["envoyes"] or 0
    total_livres = aggregate["livres"] or 0
    total_echecs = aggregate["echecs"] or 0
    taux_livraison = round((total_livres * 100 / total_envoyes), 1) if total_envoyes else 0
    taux_echec = round((total_echecs * 100 / (total_envoyes + total_echecs)), 1) if (total_envoyes + total_echecs) else 0
    stats_villes = (
        MessageEnvoi.objects.values("user__ville")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )
    stats_roles = (
        MessageEnvoi.objects.values("user__role")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )

    return render(
        request,
        "whatsapp_agent/dashboard.html",
        {
            "campagnes": campagnes,
            "statut_filter": statut,
            "statuts": Campagne.STATUTS,
            "total_campagnes": aggregate["total"] or 0,
            "total_contacts_whatsapp": ContactWhatsApp.objects.count(),
            "total_envoyes": total_envoyes,
            "taux_livraison": taux_livraison,
            "total_echecs": total_echecs,
            "taux_echec": taux_echec,
            "stats_villes": stats_villes,
            "stats_roles": stats_roles,
            "total_conversations": ConversationWhatsApp.objects.count(),
            "total_non_lus": ConversationWhatsApp.objects.filter(non_lus_count__gt=0).count(),
            "total_interesses": ConversationWhatsApp.objects.filter(statut=ConversationWhatsApp.STATUT_INTERESSE).count(),
            "whatsapp_dry_run": settings.WHATSAPP_DRY_RUN,
            "whatsapp_config_ready": settings.WHATSAPP_CONFIG_READY,
        },
    )


@staff_required
def importer_contacts(request):
    """Import manuel d'une liste de numeros WhatsApp autorises."""

    parsed_numbers = []
    if request.method == "POST":
        raw_numbers = request.POST.get("numeros", "")
        parsed_numbers = _parse_liste_numeros(raw_numbers)
        ville = request.POST.get("ville", "").strip()
        groupe = request.POST.get("groupe", "").strip()
        note = request.POST.get("note", "").strip()
        module = request.POST.get("module", "services").strip() or "services"
        consentement = request.POST.get("consentement") == "on"
        sync_commercial = request.POST.get("sync_commercial") == "on"

        if not consentement:
            messages.error(request, "Coche la confirmation: ces prospects doivent etre autorises a etre contactes.")
        elif not parsed_numbers:
            messages.error(request, "Aucun numero WhatsApp valide detecte.")
        else:
            created = 0
            updated = 0
            contact_ids = []
            for numero in parsed_numbers:
                contact, was_created = ContactWhatsApp.objects.get_or_create(
                    numero=numero,
                    defaults={
                        "ville": ville,
                        "groupe": groupe,
                        "note": note,
                        "source": ContactWhatsApp.SOURCE_MANUEL,
                        "consentement_confirme": True,
                        "consentement_source": "manual_confirmation",
                        "consentement_le": timezone.now(),
                        "importe_par": request.user,
                    },
                )
                if was_created:
                    created += 1
                else:
                    changed = False
                    for field, value in {"ville": ville, "groupe": groupe, "note": note}.items():
                        if value and getattr(contact, field) != value:
                            setattr(contact, field, value)
                            changed = True
                    if not contact.consentement_confirme and not contact.desinscrit:
                        contact.consentement_confirme = True
                        contact.consentement_source = "manual_confirmation"
                        contact.consentement_le = timezone.now()
                        changed = True
                    if changed:
                        contact.save(update_fields=["ville", "groupe", "note", "consentement_confirme", "consentement_source", "consentement_le", "mis_a_jour_le"])
                    updated += 1
                contact_ids.append(contact.id)

            extra = ""
            if sync_commercial:
                from commercial_agent.services import CommercialAgentService

                result = CommercialAgentService.sync_from_whatsapp_contacts(
                    limit=len(contact_ids),
                    assigne_a=request.user,
                    module=module,
                    contact_ids=contact_ids,
                )
                extra = (
                    f" Prospects commerciaux: {result['created']} crees, "
                    f"{result['updated']} mis a jour."
                )

            messages.success(
                request,
                f"Contacts WhatsApp importes: {created} nouveaux, {updated} existants/mis a jour.{extra}",
            )
            if sync_commercial:
                return redirect("commercial_agent:prospect_list")
            return redirect("whatsapp_agent:wa_import_contacts")

    recent_contacts = ContactWhatsApp.objects.select_related("importe_par").order_by("-cree_le")[:30]
    return render(
        request,
        "whatsapp_agent/import_contacts.html",
        {
            "recent_contacts": recent_contacts,
            "parsed_numbers": parsed_numbers,
        },
    )


@staff_required
def creer_campagne(request):
    """Creation d'une campagne en brouillon."""

    if request.method == "POST":
        form = CampagneForm(request.POST)
        selection = TemplateSelectionForm(request.POST)
        form_valid = form.is_valid()
        selection_valid = selection.is_valid()
        if form_valid and selection_valid:
            campagne = form.save(commit=False)
            selection.apply(campagne)
            campagne.cree_par = request.user
            action = request.POST.get("action", "draft")
            campagne.statut = Campagne.STATUT_VALIDEE if action == "validate" else Campagne.STATUT_BROUILLON
            campagne.save()
            _creer_messages_campagne(campagne)
            if action == "validate":
                messages.success(
                    request,
                    "Campagne validee. Verifie les destinataires puis lance l'envoi quand tu es pret.",
                )
            else:
                messages.success(request, "Campagne WhatsApp sauvegardee en brouillon.")
            return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)
    else:
        form = CampagneForm()
        selection = TemplateSelectionForm()

    return render(
        request,
        "whatsapp_agent/creer_campagne.html",
        {
            "form": form,
            "selection": selection,
            "template_key": selection.data.get('meta_template', '') if selection.is_bound else '',
            "meta_params_initial": selection.cleaned_data.get('meta_params') or [] if selection.is_bound else [],
            "ai_presets": AI_PRESETS,
            "whatsapp_dry_run": settings.WHATSAPP_DRY_RUN,
        },
    )


@staff_required
def detail_campagne(request, pk):
    """Detail d'une campagne avec progression et messages individuels."""

    campagne = get_object_or_404(Campagne.objects.select_related("cree_par"), pk=pk)
    recalculer_stats_campagne(campagne)
    messages_qs = campagne.messages.select_related("user", "commercial_prospect").order_by("-mis_a_jour_le")
    paginator = Paginator(messages_qs, 30)
    page_obj = paginator.get_page(request.GET.get("page"))
    exemples = campagne.messages.select_related("user", "commercial_prospect").order_by("id")[:5]
    if campagne.template_meta_name:
        for exemple in exemples:
            exemple.message_final = template_preview(campagne, exemple)

    return render(
        request,
        "whatsapp_agent/detail_campagne.html",
        {
            "campagne": campagne,
            "page_obj": page_obj,
            "progress_envoyes": _percent(campagne.total_envoyes, campagne.total_destinataires),
            "progress_livres": _percent(campagne.total_livres, campagne.total_destinataires),
            "progress_lus": _percent(campagne.total_lus, campagne.total_destinataires),
            "progress_echecs": _percent(campagne.total_echecs, campagne.total_destinataires),
            "exemples": exemples,
            "whatsapp_dry_run": settings.WHATSAPP_DRY_RUN,
            "whatsapp_config_ready": settings.WHATSAPP_CONFIG_READY,
            "contacts_selectionnes": campagne.destinataires_contacts.count(),
            "tests_envoi": campagne.tests_envoi.all()[:5],
            "template_key": campagne.template_meta_name + '|' + campagne.template_meta_language if campagne.template_meta_name else '',
        },
    )


def _percent(value, total):
    return round(value * 100 / total) if total else 0


@staff_required
@require_POST
def lancer_campagne(request, pk):
    """Declenche la tache Celery d'envoi massif."""

    campagne = get_object_or_404(Campagne, pk=pk)
    confirmation = request.POST.get("confirm_launch") == "on"
    if campagne.statut != Campagne.STATUT_VALIDEE:
        messages.warning(request, "Valide d'abord la campagne avant de lancer l'envoi.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)
    if not confirmation:
        messages.warning(request, "Coche la confirmation finale avant de lancer la campagne.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)
    if campagne.template_meta_name:
        try:
            validate_selection(campagne.template_meta_name + '|' + campagne.template_meta_language,
                campagne.template_meta_params, refresh=True)
        except TemplateError as exc:
            messages.error(request, str(exc))
            return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)
    # Freeze the configuration before queueing, including the gap before Celery starts.
    claimed = Campagne.objects.filter(pk=campagne.pk, statut=Campagne.STATUT_VALIDEE,
        template_meta_name=campagne.template_meta_name,
        template_meta_language=campagne.template_meta_language,
        template_meta_params=campagne.template_meta_params).update(statut=Campagne.STATUT_EN_COURS)
    if not claimed:
        messages.warning(request, 'Cette campagne a ete lancee ou modifiee. Actualise la page avant de continuer.')
        return redirect('whatsapp_agent:wa_detail', pk=campagne.pk)
    if settings.WHATSAPP_DRY_RUN:
        lancer_campagne_direct(campagne.pk)
        messages.success(request, "Simulation terminee: les messages ont ete marques comme envoyes sans appel Meta.")
    else:
        try:
            lancer_campagne_task.delay(campagne.pk)
            messages.success(request, "Lancement reel de la campagne programme.")
        except Exception as exc:
            Campagne.objects.filter(pk=campagne.pk, statut=Campagne.STATUT_EN_COURS, lance_le__isnull=True).update(statut=Campagne.STATUT_VALIDEE)
            messages.error(
                request,
                f"Celery/Redis indisponible: impossible de lancer l'envoi reel. Detail: {exc}",
            )
    return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)


@staff_required
@require_POST
def envoyer_test_campagne(request, pk):
    """Envoie le premier message de la campagne vers un numero de test."""

    campagne = get_object_or_404(Campagne, pk=pk)
    numero_test = WhatsAppService.normaliser_numero(request.POST.get("numero_test", ""))
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", numero_test):
        messages.warning(request, "Entre ton numero WhatsApp de test avant l'envoi.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)

    exemple = campagne.messages.order_by("id").first()
    if not exemple:
        messages.warning(request, "Aucun message prepare dans cette campagne.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)

    template_name = request.POST.get("template_name", "").strip()
    template_language = request.POST.get("template_language", "").strip()
    try:
        raw_params = request.POST.get("template_params", "").strip()
        params = json.loads(raw_params) if raw_params else [request.user.first_name or "Client"]
        if not isinstance(params, list) or len(params) > 20 or not all(isinstance(p, str) and len(p) <= 1024 for p in params):
            raise ValueError("invalid parameters")
    except (ValueError, TypeError):
        messages.error(request, 'Parametres invalides : utilise une liste JSON, par exemple ["Leonel"].')
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)
    if (template_name and not re.fullmatch(r"[a-z0-9_]{1,512}", template_name)) or (template_language and not re.fullmatch(r"[a-z]{2,3}(?:_[A-Z]{2})?", template_language)):
        messages.error(request, "Nom de modele ou code de langue invalide.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)
    if campagne.template_meta_name:
        try:
            validate_selection(campagne.template_meta_name + '|' + campagne.template_meta_language,
                campagne.template_meta_params, refresh=True)
        except TemplateError as exc:
            messages.error(request, str(exc))
            return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)
        template_name = campagne.template_meta_name
        template_language = campagne.template_meta_language
        params = message_parameters(campagne, exemple)
    message_test = exemple.message_final if exemple.message_final.strip().startswith("template:") else (
        "[TEST E-SHELLE]\n"
        f"Campagne: {campagne.nom}\n\n"
        f"{exemple.message_final}"
    )
    test = WhatsAppTestSend.objects.create(campagne=campagne, numero=numero_test)
    result = WhatsAppService.envoyer_message(numero_test, message_test, template_name=template_name,
        template_params=params, template_language=template_language)
    test.whatsapp_message_id = result.get("message_id", "")
    test.statut = ("simulation" if settings.WHATSAPP_DRY_RUN else "accepte") if result["success"] else "echec"
    test.erreur = result.get("erreur", "")
    test.save(update_fields=["whatsapp_message_id", "statut", "erreur", "mis_a_jour_le"])
    if result["success"]:
        if settings.WHATSAPP_DRY_RUN:
            messages.success(
                request,
                f"Test simule avec succes vers {numero_test}. Active Meta pour recevoir le message reel.",
            )
        else:
            messages.success(request, f"Test accepte par Meta vers {numero_test}. La livraison reste a confirmer dans le suivi ci-dessous.")
    else:
        messages.error(request, f"Echec du test WhatsApp: {result['erreur']}")
    return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)


def _copier_message_envoi(campagne, source_message, message_final=None):
    return MessageEnvoi(
        campagne=campagne,
        user=source_message.user,
        commercial_prospect=source_message.commercial_prospect,
        destinataire_nom=source_message.destinataire_nom,
        numero_whatsapp=source_message.numero_whatsapp,
        message_final=message_final or source_message.message_final,
    )


@staff_required
@require_POST
def dupliquer_campagne(request, pk):
    """Cree une nouvelle campagne validee avec les memes destinataires et messages."""

    campagne = get_object_or_404(Campagne, pk=pk)
    copie = Campagne.objects.create(
        nom=f"Copie - {campagne.nom}",
        description=f"Copie de la campagne #{campagne.pk}. Verifie avant lancement.",
        message_template=campagne.message_template,
        template_meta_name=campagne.template_meta_name,
        template_meta_language=campagne.template_meta_language,
        template_meta_params=campagne.template_meta_params,
        template_meta_preview=campagne.template_meta_preview,
        statut=Campagne.STATUT_VALIDEE,
        filtre_role=campagne.filtre_role,
        filtre_ville=campagne.filtre_ville,
        filtre_date_inscription_depuis=campagne.filtre_date_inscription_depuis,
        cree_par=request.user,
    )
    copie.destinataires_contacts.set(campagne.destinataires_contacts.all())
    messages_source = campagne.messages.select_related("user", "commercial_prospect").order_by("id")
    MessageEnvoi.objects.bulk_create(
        [_copier_message_envoi(copie, item) for item in messages_source],
        batch_size=500,
    )
    recalculer_stats_campagne(copie)
    messages.success(request, f"Campagne dupliquee avec {copie.total_destinataires} destinataire(s).")
    return redirect("whatsapp_agent:wa_detail", pk=copie.pk)


@staff_required
@require_POST
def relancer_non_repondants(request, pk):
    """Cree une campagne de relance depuis les messages deja envoyes."""

    campagne = get_object_or_404(Campagne, pk=pk)
    candidats = campagne.messages.filter(
        statut__in=[
            MessageEnvoi.STATUT_ENVOYE,
            MessageEnvoi.STATUT_LIVRE,
            MessageEnvoi.STATUT_LU,
        ]
    ).select_related("user", "commercial_prospect").order_by("id")

    if not candidats.exists():
        messages.warning(request, "Aucun destinataire envoye a relancer pour cette campagne.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)

    relance = Campagne.objects.create(
        nom=f"Relance - {campagne.nom}",
        description=f"Relance creee depuis la campagne #{campagne.pk}. Verifie avant lancement.",
        message_template="Relance commerciale personnalisee.",
        statut=Campagne.STATUT_VALIDEE,
        filtre_role=campagne.filtre_role,
        filtre_ville=campagne.filtre_ville,
        filtre_date_inscription_depuis=campagne.filtre_date_inscription_depuis,
        cree_par=request.user,
    )

    nouveaux_messages = []
    for item in candidats:
        nom = item.destinataire_label
        message_final = (
            f"Bonjour {nom}, je reviens vers vous concernant mon precedent message E-Shelle. "
            "Souhaitez-vous une demo rapide ou plus d'informations sur l'offre ?"
        )
        nouveaux_messages.append(_copier_message_envoi(relance, item, message_final=message_final))

    MessageEnvoi.objects.bulk_create(nouveaux_messages, batch_size=500)
    recalculer_stats_campagne(relance)
    messages.success(request, f"Campagne de relance creee avec {relance.total_destinataires} destinataire(s).")
    return redirect("whatsapp_agent:wa_detail", pk=relance.pk)


@staff_required
def export_csv(request, pk):
    """Export CSV des messages d'une campagne."""

    campagne = get_object_or_404(Campagne, pk=pk)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="campagne-whatsapp-{campagne.pk}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Campagne", "Utilisateur", "Numero", "Statut", "Message ID", "Erreur", "Envoye le"])
    for msg in campagne.messages.select_related("user", "commercial_prospect").order_by("id"):
        writer.writerow([campagne.nom, msg.destinataire_label, msg.numero_whatsapp, msg.statut, msg.whatsapp_message_id, msg.erreur, msg.envoye_le])
    return response


@staff_required
@require_POST
def api_generer_message(request):
    """API AJAX qui genere un message marketing avec les fournisseurs IA configurés."""

    data = _json_body(request)
    try:
        preset = AI_PRESETS.get(data.get("preset", ""), {})
        message = WhatsAppService.generer_message_ia(
            data.get("segment") or preset.get("segment", ""),
            data.get("contexte") or preset.get("contexte", ""),
        )
        return JsonResponse({"message": message})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@staff_required
@require_POST
def api_apercu_contacts(request):
    """API AJAX qui retourne le nombre et quelques exemples de contacts."""

    data = _json_body(request)
    contacts = WhatsAppService.recuperer_contacts(
        data.get("filtre_role", ""),
        data.get("filtre_ville", ""),
        data.get("date_depuis") or None,
    )
    exemples = []
    for user in contacts[:5]:
        exemples.append(
            {
                "prenom": user.first_name or user.username,
                "ville": user.ville or getattr(getattr(user, "profile", None), "ville", ""),
                "role": user.role,
            }
        )
    return JsonResponse({"total": contacts.count(), "exemples": exemples})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_import_contact(request):
    """Importe un contact WhatsApp autorise depuis un outil local ou une integration."""

    data = request.data
    numero = WhatsAppService.normaliser_numero(str(data.get("numero") or data.get("phone") or "").strip())
    if not numero:
        return Response({"error": "Le numero WhatsApp est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)

    consentement = data.get("consentement_confirme", data.get("consent", False))
    if isinstance(consentement, str):
        consentement = consentement.lower() in ("1", "true", "yes", "oui")

    if not consentement:
        return Response(
            {"error": "Import refuse: le consentement du contact doit etre confirme."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    defaults = {
        "nom": str(data.get("nom") or data.get("name") or "").strip(),
        "ville": str(data.get("ville") or data.get("city") or "").strip(),
        "groupe": str(data.get("groupe") or data.get("group") or "").strip(),
        "source": str(data.get("source") or ContactWhatsApp.SOURCE_API).strip()[:20],
        "note": str(data.get("note") or "").strip(),
        "consentement_confirme": True,
        "consentement_source": str(data.get("consentement_source") or "api_confirmation").strip()[:80],
        "consentement_le": timezone.now(),
        "importe_par": request.user if request.user.is_authenticated else None,
    }
    contact, created = ContactWhatsApp.objects.get_or_create(numero=numero, defaults=defaults)
    if not created:
        updated = False
        for field in ["nom", "ville", "groupe", "source", "note"]:
            value = defaults[field]
            if value and getattr(contact, field) != value:
                setattr(contact, field, value)
                updated = True
        if not contact.consentement_confirme and not contact.desinscrit:
            contact.consentement_confirme = True
            contact.consentement_source = defaults["consentement_source"]
            contact.consentement_le = defaults["consentement_le"]
            updated = True
        if updated:
            contact.save(update_fields=["nom", "ville", "groupe", "source", "note", "consentement_confirme", "consentement_source", "consentement_le", "mis_a_jour_le"])
        return Response(
            {"status": "exists", "id": contact.id, "numero": contact.numero},
            status=status.HTTP_200_OK,
        )

    return Response(
        {"status": "created", "id": contact.id, "numero": contact.numero},
        status=status.HTTP_201_CREATED,
    )


@csrf_exempt
def webhook_meta(request):
    """Webhook Meta: verification GET puis reception des statuts et reponses prospects POST."""

    if request.method == "GET":
        verify_token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        configured_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "")
        if configured_token and hmac.compare_digest(verify_token or "", configured_token) and challenge:
            return HttpResponse(challenge)
        return HttpResponse("Token invalide", status=403)

    if request.method != "POST":
        return HttpResponse(status=405)

    if request.content_type != "application/json":
        return JsonResponse({"error": "Content-Type application/json requis"}, status=415)

    signature = request.headers.get("X-Hub-Signature-256", "")
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
    if not app_secret:
        return HttpResponse("Signature webhook non configuree", status=503)
    expected = "sha256=" + hmac.new(app_secret.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return HttpResponse("Signature invalide", status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "JSON invalide"}, status=400)
    if not isinstance(data, dict) or data.get("object") != "whatsapp_business_account":
        return JsonResponse({"error": "Payload WhatsApp invalide"}, status=400)

    for entry in data.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict):
                continue
            value = change.get("value", {})
            if not isinstance(value, dict):
                continue

            # 1. Extraction des profils WhatsApp des contacts
            profile_names = {}
            for ct in value.get("contacts", []):
                if isinstance(ct, dict):
                    wa_id = ct.get("wa_id", "")
                    p_name = ct.get("profile", {}).get("name", "")
                    if wa_id and p_name:
                        profile_names[wa_id] = p_name

            _handle_call_events(value, profile_names)

            # 2. Reception et enregistrement des reponses des prospects
            for incoming in value.get("messages", []):
                if not isinstance(incoming, dict):
                    continue
                from_raw = incoming.get("from", "")
                numero = WhatsAppService.normaliser_numero(from_raw)
                wa_msg_id = incoming.get("id", "")
                msg_type = incoming.get("type", "text")
                profile_name = profile_names.get(from_raw, "")

                body_text = ""
                media_url = ""
                media_id = ""
                doc_filename = ""
                mime_type = ""
                if wa_msg_id and MessageWhatsApp.objects.filter(whatsapp_msg_id=wa_msg_id).exists():
                    continue
                if msg_type == "text":
                    body_text = (incoming.get("text", {}).get("body") or "").strip()
                elif msg_type == "button":
                    body_text = (incoming.get("button", {}).get("text") or "").strip()
                elif msg_type == "interactive":
                    interactive = incoming.get("interactive", {})
                    if "button_reply" in interactive:
                        body_text = interactive["button_reply"].get("title", "")
                    elif "list_reply" in interactive:
                        body_text = interactive["list_reply"].get("title", "")
                    elif interactive.get("type") == "call_permission_reply":
                        reply = interactive.get("call_permission_reply", {})
                        permission_status = "no_permission"
                        expiration = None
                        if reply.get("response") == "accept":
                            permission_status = "permanent" if reply.get("is_permanent") else "temporary"
                            expiration = _meta_message_time(reply.get("expiration_timestamp"))
                        ContactWhatsApp.objects.filter(numero=numero).update(
                            call_permission_status=permission_status,
                            call_permission_expires_at=expiration,
                            mis_a_jour_le=timezone.now(),
                        )
                        body_text = "Autorisation d’appel accordée" if permission_status != "no_permission" else "Autorisation d’appel refusée"
                elif msg_type in ["image", "audio", "document", "video", "sticker"]:
                    media_obj = incoming.get(msg_type, {})
                    caption = (media_obj.get("caption") or "").strip()
                    doc_filename = (media_obj.get("filename") or "").strip()
                    media_id = (media_obj.get("id") or "").strip()
                    mime_type = (media_obj.get("mime_type") or "").strip()

                    # Texte représentatif : légende si présente, sinon nom du document, sinon étiquette claire
                    if caption:
                        body_text = caption
                    elif doc_filename:
                        body_text = doc_filename
                    else:
                        labels = {
                            "image": "📷 Photo",
                            "document": "📄 Document",
                            "audio": "🎤 Note vocale",
                            "video": "🎥 Vidéo",
                            "sticker": "Sticker",
                        }
                        body_text = labels.get(msg_type, f"[{msg_type.upper()}]")

                    # Acknowledge webhooks promptly; fetch bytes through the authenticated media endpoint.
                    # Keeping the Meta ID allows a fresh download URL on retry.
                    media_url = media_id

                text_lower = body_text.lower()

                # Desinscription opt-out
                if text_lower in {"stop", "arret", "arrêt", "desinscrire", "désinscrire", "unsubscribe"}:
                    if numero:
                        ContactWhatsApp.objects.filter(numero=numero).update(
                            desinscrit=True,
                            desinscrit_le=timezone.now(),
                            consentement_confirme=False,
                            mis_a_jour_le=timezone.now(),
                        )
                        get_user_model().objects.filter(whatsapp=numero).update(
                            whatsapp_marketing_opt_in=False,
                            whatsapp_marketing_opted_out=True,
                        )
                    continue

                # Message entrant normal (reponse du prospect)
                if numero and (body_text or media_url):
                    WhatsAppService.enregistrer_message_entrant(
                        numero=numero,
                        texte=body_text,
                        whatsapp_msg_id=wa_msg_id,
                        profile_name=profile_name,
                        media_type=msg_type,
                        media_url=media_url,
                        media_id=media_id,
                        media_filename=doc_filename[:255],
                        media_mime_type=mime_type[:150],
                        meta_timestamp=_meta_message_time(incoming.get('timestamp')),
                    )

            # 3. Statuts de remise des messages sortants
            for status in value.get("statuses", []):
                message_id = status.get("id", "")
                wa_status = status.get("status", "")
                nouveau_statut = {"sent": "envoye", "delivered": "livre", "read": "lu", "failed": "echec"}.get(wa_status)
                if message_id and nouveau_statut:
                    update_data = {"statut": nouveau_statut, "mis_a_jour_le": timezone.now()}
                    if nouveau_statut == "echec":
                        update_data["erreur"] = str(status.get("errors", ""))
                    test_qs = WhatsAppTestSend.objects.filter(whatsapp_message_id=message_id)
                    if nouveau_statut == "envoye":
                        test_qs = test_qs.exclude(statut__in=["livre", "lu", "echec"])
                    elif nouveau_statut == "livre":
                        test_qs = test_qs.exclude(statut__in=["lu", "echec"])
                    elif nouveau_statut == "echec":
                        test_qs = test_qs.exclude(statut__in=["livre", "lu"])
                    test_qs.update(**update_data)
                    MessageEnvoi.objects.filter(whatsapp_message_id=message_id).update(**update_data)
                    MessageWhatsApp.objects.filter(whatsapp_msg_id=message_id).update(
                        statut=nouveau_statut, erreur=str(status.get('errors', '')) if nouveau_statut == 'echec' else '')
                    for campagne in Campagne.objects.filter(messages__whatsapp_message_id=message_id).distinct():
                        recalculer_stats_campagne(campagne)

    return JsonResponse({"status": "ok"})


@staff_required
def inbox_whatsapp(request):
    """Boite de reception (Inbox) en temps reel des reponses WhatsApp."""

    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "").strip()
    groupe = request.GET.get("groupe", "").strip()
    active_id = request.GET.get("conv", "").strip()

    conversations = ConversationWhatsApp.objects.select_related("contact", "commercial_prospect", "assigne_a").order_by("-dernier_message_le", "-mis_a_jour_le")

    if q:
        conversations = conversations.filter(
            Q(contact__nom__icontains=q)
            | Q(contact__numero__icontains=q)
            | Q(dernier_message_apercu__icontains=q)
            | Q(notes__icontains=q)
        )
    if statut:
        if statut == "non_lus":
            conversations = conversations.filter(non_lus_count__gt=0)
        else:
            conversations = conversations.filter(statut=statut)
    if groupe:
        conversations = conversations.filter(contact__groupe__icontains=groupe)

    total_convs = ConversationWhatsApp.objects.count()
    total_non_lus = ConversationWhatsApp.objects.filter(non_lus_count__gt=0).count()
    total_interesses = ConversationWhatsApp.objects.filter(statut=ConversationWhatsApp.STATUT_INTERESSE).count()
    total_qualifies = ConversationWhatsApp.objects.filter(statut=ConversationWhatsApp.STATUT_QUALIFIE).count()

    active_conv = None
    if active_id and active_id.isdigit():
        active_conv = conversations.filter(id=int(active_id)).first()
    if not active_conv and conversations.exists():
        active_conv = conversations.first()

    messages_active = []
    if active_conv:
        messages_active = active_conv.messages.select_related("envoye_par").order_by("cree_le")
        if active_conv.non_lus_count > 0:
            active_conv.non_lus_count = 0
            active_conv.save(update_fields=["non_lus_count"])

    groupes_dispos = ContactWhatsApp.objects.exclude(groupe="").values_list("groupe", flat=True).distinct()[:15]

    return render(
        request,
        "whatsapp_agent/inbox.html",
        {
            "conversations": conversations[:100],
            "active_conv": active_conv,
            "messages_active": messages_active,
            "q": q,
            "statut": statut,
            "groupe": groupe,
            "groupes_dispos": groupes_dispos,
            "total_convs": total_convs,
            "total_non_lus": total_non_lus,
            "total_interesses": total_interesses,
            "total_qualifies": total_qualifies,
            "statuts_conv": ConversationWhatsApp.STATUTS,
            "priorites_conv": ConversationWhatsApp.PRIORITES,
            "whatsapp_dry_run": settings.WHATSAPP_DRY_RUN,
            "whatsapp_config_ready": settings.WHATSAPP_CONFIG_READY,
        },
    )


@staff_required
def api_conversations_list(request):
    """Retourne la liste des conversations en JSON pour auto-refresh."""
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "").strip()

    conversations = ConversationWhatsApp.objects.select_related("contact").order_by("-dernier_message_le")
    if q:
        conversations = conversations.filter(
            Q(contact__nom__icontains=q) | Q(contact__numero__icontains=q) | Q(dernier_message_apercu__icontains=q)
        )
    if statut:
        if statut == "non_lus":
            conversations = conversations.filter(non_lus_count__gt=0)
        else:
            conversations = conversations.filter(statut=statut)

    items = []
    for c in conversations[:60]:
        items.append({
            "id": c.id,
            "nom": c.contact.nom or f"Contact {c.contact.numero}",
            "numero": c.contact.numero,
            "ville": c.contact.ville or "",
            "groupe": c.contact.groupe or "",
            "statut": c.statut,
            "statut_display": c.get_statut_display(),
            "priorite": c.priorite,
            "dernier_message": c.dernier_message_apercu or "",
            "heure": c.dernier_message_le.strftime("%H:%M") if c.dernier_message_le else "",
            "date": c.dernier_message_le.strftime("%d/%m") if c.dernier_message_le else "",
            "non_lus": c.non_lus_count,
        })
    total_non_lus = ConversationWhatsApp.objects.filter(non_lus_count__gt=0).count()
    return JsonResponse({"conversations": items, "total_non_lus": total_non_lus})


@staff_required
def api_conversation_detail(request, pk):
    """Charge l'historique d'une conversation et efface les non-lus."""
    conv = get_object_or_404(ConversationWhatsApp.objects.select_related("contact", "commercial_prospect"), pk=pk)
    if conv.non_lus_count > 0:
        conv.non_lus_count = 0
        conv.save(update_fields=["non_lus_count"])

    messages_list = []
    for m in conv.messages.select_related("envoye_par").order_by("cree_le"):
        messages_list.append({
            "id": m.id,
            "direction": m.direction,
            "texte": m.texte,
            "statut": m.statut,
            "media_type": m.media_type,
            "media_download_url": m.media_download_url,
            "has_media": m.has_media,
            "media_size": m.media_size,
            "erreur": m.erreur,
            "is_image": m.is_image,
            "is_document": m.is_document,
            "is_audio": m.is_audio,
            "is_video": m.is_video,
            "display_filename": m.display_filename,
            "auteur": m.envoye_par.get_full_name() or m.envoye_par.username if m.envoye_par else "E-Shelle",
            "heure": m.cree_le.strftime("%H:%M"),
            "date": m.cree_le.strftime("%d/%m/%Y"),
        })

    contact = conv.contact
    prospect_id = conv.commercial_prospect_id or None
    prospect_nom = conv.commercial_prospect.nom if conv.commercial_prospect else ""

    return JsonResponse({
        "conversation": {
            "id": conv.id,
            "nom": contact.nom or f"Contact {contact.numero}",
            "numero": contact.numero,
            "ville": contact.ville or "",
            "groupe": contact.groupe or "",
            "source": contact.get_source_display(),
            "statut": conv.statut,
            "statut_display": conv.get_statut_display(),
            "priorite": conv.priorite,
            "notes": conv.notes,
            "commercial_prospect_id": prospect_id,
            "commercial_prospect_nom": prospect_nom,
        },
        "messages": messages_list,
    })


@staff_required
def api_conversation_calls(request, pk):
    if request.method != "GET":
        return JsonResponse({"error": "Méthode non autorisée."}, status=405)
    conversation = get_object_or_404(ConversationWhatsApp.objects.select_related("contact"), pk=pk)
    calls = conversation.calls.order_by("-created_at")[:5]
    return JsonResponse({"calls": [{
        "id": call.pk,
        "meta_call_id": call.meta_call_id,
        "direction": call.direction,
        "status": call.status,
        "sdp_offer": call.sdp_offer if call.direction == WhatsAppCall.DIRECTION_INBOUND and call.status == WhatsAppCall.STATUS_RINGING else "",
        "sdp_answer": call.sdp_answer if call.direction == WhatsAppCall.DIRECTION_OUTBOUND and call.status == WhatsAppCall.STATUS_CONNECTING else "",
        "error": call.error,
        "updated_at": call.updated_at.isoformat(),
    } for call in calls]})


@staff_required
def api_pending_calls(request):
    if request.method != "GET":
        return JsonResponse({"error": "Méthode non autorisée."}, status=405)
    calls = WhatsAppCall.objects.filter(
        status__in=[WhatsAppCall.STATUS_RINGING, WhatsAppCall.STATUS_CONNECTING, WhatsAppCall.STATUS_ACTIVE]
    ).select_related("contact", "conversation").order_by("created_at")[:20]
    return JsonResponse({"calls": [{
        "id": call.pk,
        "conversation_id": call.conversation_id,
        "contact_name": call.contact.nom or call.contact.numero,
        "number": call.contact.numero,
        "direction": call.direction,
        "status": call.status,
        "sdp_offer": call.sdp_offer if call.direction == WhatsAppCall.DIRECTION_INBOUND and call.status == WhatsAppCall.STATUS_RINGING else "",
        "sdp_answer": call.sdp_answer if call.direction == WhatsAppCall.DIRECTION_OUTBOUND and call.status == WhatsAppCall.STATUS_CONNECTING else "",
        "error": call.error,
    } for call in calls]})


@staff_required
@require_POST
def api_request_call_permission(request, pk):
    conversation = get_object_or_404(ConversationWhatsApp.objects.select_related("contact"), pk=pk)
    context = _json_body(request).get("context") or "E-Shelle souhaite vous appeler sur WhatsApp afin de répondre à votre demande. Autorisez l’appel si cela vous convient."
    try:
        result = request_call_permission(conversation.contact.numero, context)
    except WhatsAppCallingError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    return JsonResponse({"success": True, "message_id": result.get("messages", [{}])[0].get("id", "")})


@staff_required
@require_POST
def api_start_call(request, pk):
    conversation = get_object_or_404(ConversationWhatsApp.objects.select_related("contact"), pk=pk)
    body = _json_body(request)
    sdp_offer = body.get("sdp_offer", "")
    if not isinstance(sdp_offer, str) or not sdp_offer.startswith("v=") or len(sdp_offer) > 30000:
        return JsonResponse({"error": "Offre WebRTC invalide."}, status=400)
    try:
        permission = get_call_permission(conversation.contact.numero)
    except WhatsAppCallingError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    permission_info = permission.get("permission", {})
    actions = {item.get("action_name"): item for item in permission.get("actions", [])}
    allowed = permission_info.get("status") in ("temporary", "permanent")
    start_action = actions.get("start_call", {})
    if not allowed or start_action.get("can_perform_action") is not True:
        return JsonResponse({"error": "Le contact doit d’abord autoriser les appels WhatsApp."}, status=403)
    contact = conversation.contact
    contact.call_permission_status = permission_info.get("status", "no_permission")
    expires = permission_info.get("expiration_time") or permission_info.get("expiration")
    contact.call_permission_expires_at = _meta_message_time(expires) if expires else None
    contact.save(update_fields=["call_permission_status", "call_permission_expires_at", "mis_a_jour_le"])
    call = WhatsAppCall.objects.create(
        conversation=conversation,
        contact=contact,
        initiated_by=request.user,
        direction=WhatsAppCall.DIRECTION_OUTBOUND,
        status=WhatsAppCall.STATUS_PENDING,
        sdp_offer=sdp_offer,
    )
    try:
        result = initiate_call(contact.numero, sdp_offer, str(call.pk))
    except WhatsAppCallingError as exc:
        call.status = WhatsAppCall.STATUS_FAILED
        call.error = str(exc)
        call.save(update_fields=["status", "error", "updated_at"])
        return JsonResponse({"error": str(exc)}, status=502)
    call_info = (result.get("calls") or [{}])[0]
    if not call_info.get("id"):
        call.status = WhatsAppCall.STATUS_FAILED
        call.error = "Meta n’a pas retourné d’identifiant d’appel."
        call.save(update_fields=["status", "error", "updated_at"])
        return JsonResponse({"error": call.error}, status=502)
    call.meta_call_id = call_info["id"]
    call.status = WhatsAppCall.STATUS_CONNECTING
    call.save(update_fields=["meta_call_id", "status", "updated_at"])
    return JsonResponse({"success": True, "call_id": call.pk})


@staff_required
@require_POST
def api_call_action(request, pk):
    call = get_object_or_404(WhatsAppCall.objects.select_related("conversation"), pk=pk)
    body = _json_body(request)
    action = body.get("action")
    if action not in {"pre_accept", "accept", "reject", "terminate", "media_connected"}:
        return JsonResponse({"error": "Action d’appel invalide."}, status=400)
    if action == "media_connected" and call.direction != WhatsAppCall.DIRECTION_OUTBOUND:
        return JsonResponse({"error": "Action non autorisée pour cet appel."}, status=400)
    if call.direction != WhatsAppCall.DIRECTION_INBOUND and action not in {"terminate", "media_connected"}:
        return JsonResponse({"error": "Action non autorisée pour cet appel."}, status=400)
    if call.direction == WhatsAppCall.DIRECTION_INBOUND:
        if action == "pre_accept":
            claimed = WhatsAppCall.objects.filter(
                pk=call.pk,
                status=WhatsAppCall.STATUS_RINGING,
                initiated_by__isnull=True,
            ).update(
                status=WhatsAppCall.STATUS_CONNECTING,
                initiated_by=request.user,
                updated_at=timezone.now(),
            )
            if not claimed:
                return JsonResponse({"error": "Cet appel est déjà pris en charge ou terminé."}, status=409)
            call.refresh_from_db()
        elif call.initiated_by_id and call.initiated_by_id != request.user.pk:
            return JsonResponse({"error": "Cet appel est pris en charge par un autre agent."}, status=409)
        elif action == "accept" and call.status != WhatsAppCall.STATUS_CONNECTING:
            return JsonResponse({"error": "Pré-accepte d’abord cet appel."}, status=409)
    session = None
    if action in {"pre_accept", "accept"}:
        sdp_answer = body.get("sdp_answer", "")
        if not isinstance(sdp_answer, str) or not sdp_answer.startswith("v=") or len(sdp_answer) > 30000:
            return JsonResponse({"error": "Réponse WebRTC invalide."}, status=400)
        session = {"sdp_type": "answer", "sdp": sdp_answer}
    if not call.meta_call_id:
        return JsonResponse({"error": "Identifiant Meta de l’appel absent."}, status=409)
    if action != "media_connected":
        try:
            post_call_action(call.meta_call_id, action, session)
        except WhatsAppCallingError as exc:
            call.error = str(exc)
            fields = ["error", "updated_at"]
            if action == "pre_accept":
                call.status = WhatsAppCall.STATUS_RINGING
                call.initiated_by = None
                fields.extend(["status", "initiated_by"])
            call.save(update_fields=fields)
            return JsonResponse({"error": str(exc)}, status=502)
    if action == "reject":
        call.status = WhatsAppCall.STATUS_REJECTED
    elif action == "terminate":
        call.status = WhatsAppCall.STATUS_ENDED
        call.sdp_offer = ""
        call.sdp_answer = ""
    elif action == "pre_accept":
        call.status = WhatsAppCall.STATUS_CONNECTING
        call.sdp_answer = ""
    elif action == "accept":
        call.status = WhatsAppCall.STATUS_ACTIVE
        call.sdp_offer = ""
        call.sdp_answer = ""
    elif action == "media_connected":
        call.status = WhatsAppCall.STATUS_ACTIVE
        call.sdp_offer = ""
        call.sdp_answer = ""
    call.save(update_fields=["status", "sdp_offer", "sdp_answer", "updated_at"])
    return JsonResponse({"success": True, "status": call.status})


def _meta_message_time(value):
    try:
        from datetime import datetime, timezone as dt_timezone
        return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _handle_call_events(value, profile_names):
    for event in value.get("calls", []):
        if not isinstance(event, dict):
            continue
        meta_call_id = event.get("id", "")
        callback_data = event.get("biz_opaque_callback_data", "")
        call = WhatsAppCall.objects.filter(meta_call_id=meta_call_id).first() if meta_call_id else None
        if call is None and str(callback_data).isdigit():
            call = WhatsAppCall.objects.filter(pk=int(callback_data)).first()

        direction = event.get("direction", "")
        event_name = event.get("event", "")
        if direction == "USER_INITIATED" and event_name == "connect":
            if not meta_call_id:
                continue
            numero = WhatsAppService.normaliser_numero(event.get("from", ""))
            if not numero:
                continue
            contact, _ = ContactWhatsApp.objects.get_or_create(
                numero=numero,
                defaults={
                    "nom": profile_names.get(event.get("from", ""), ""),
                    "source": ContactWhatsApp.SOURCE_API,
                },
            )
            profile_name = profile_names.get(event.get("from", ""), "")
            if profile_name and not contact.nom:
                contact.nom = profile_name
                contact.save(update_fields=["nom", "mis_a_jour_le"])
            conversation, _ = ConversationWhatsApp.objects.get_or_create(
                contact=contact,
                defaults={"statut": ConversationWhatsApp.STATUT_NOUVEAU},
            )
            call, created = WhatsAppCall.objects.get_or_create(
                meta_call_id=meta_call_id,
                defaults={
                    "conversation": conversation,
                    "contact": contact,
                    "direction": WhatsAppCall.DIRECTION_INBOUND,
                    "status": WhatsAppCall.STATUS_RINGING,
                    "sdp_offer": (event.get("session") or {}).get("sdp", ""),
                },
            )
            if created:
                conversation.dernier_message_apercu = "Appel WhatsApp entrant"
                conversation.dernier_message_le = timezone.now()
                conversation.non_lus_count += 1
                conversation.save(update_fields=["dernier_message_apercu", "dernier_message_le", "non_lus_count", "mis_a_jour_le"])
            continue

        if call is None:
            continue
        if event_name == "connect" and call.direction == WhatsAppCall.DIRECTION_OUTBOUND:
            answer = (event.get("session") or {}).get("sdp", "")
            if not answer:
                answer = (event.get("connection", {}).get("webrtc") or {}).get("sdp", "")
            if answer:
                call.sdp_answer = answer
                call.status = WhatsAppCall.STATUS_CONNECTING
                call.error = ""
                call.save(update_fields=["sdp_answer", "status", "error", "updated_at"])
        elif event_name == "terminate":
            call.status = WhatsAppCall.STATUS_ENDED if event.get("status") == "COMPLETED" else WhatsAppCall.STATUS_FAILED
            call.duration_seconds = int(event.get("duration") or 0)
            call.sdp_offer = ""
            call.sdp_answer = ""
            errors = event.get("errors") or []
            call.error = str(errors[0].get("message", ""))[:1000] if errors else ""
            call.save(update_fields=["status", "duration_seconds", "sdp_offer", "sdp_answer", "error", "updated_at"])

    for status_item in value.get("statuses", []):
        if not isinstance(status_item, dict) or status_item.get("type") != "call":
            continue
        call = WhatsAppCall.objects.filter(meta_call_id=status_item.get("id", "")).first()
        if not call:
            continue
        call.status = {
            "RINGING": WhatsAppCall.STATUS_RINGING,
            "ACCEPTED": WhatsAppCall.STATUS_ACTIVE,
            "REJECTED": WhatsAppCall.STATUS_REJECTED,
        }.get(status_item.get("status"), call.status)
        fields = ["status", "updated_at"]
        if call.status == WhatsAppCall.STATUS_REJECTED:
            call.sdp_offer = ""
            call.sdp_answer = ""
            fields.extend(["sdp_offer", "sdp_answer"])
        call.save(update_fields=fields)


@staff_required
def serve_whatsapp_media(request, pk):
    """Stream attachments through an authenticated endpoint, including private uploads."""
    from .media import private_storage, clean_filename
    msg = get_object_or_404(MessageWhatsApp, pk=pk)
    if not msg.has_media:
        raise Http404('Aucune pièce jointe.')
    value = (msg.media_url or '').strip()
    prefix = getattr(settings, 'MEDIA_URL', '/media/')

    def open_saved(stored):
        if stored.startswith('private:'):
            storage, key = private_storage(), stored.removeprefix('private:')
        elif stored.startswith(('http://', 'https://')):
            # Legacy storage URLs; all new files are streamed from private storage.
            return HttpResponseRedirect(stored)
        else:
            storage = default_storage
            key = stored[len(prefix):] if stored.startswith(prefix) else stored
        try:
            if not key or not storage.exists(key):
                return None
            mime = msg.media_mime_type or mimetypes.guess_type(key)[0] or 'application/octet-stream'
            inline_types = {'image/jpeg', 'image/png', 'image/webp', 'audio/mpeg', 'audio/mp4',
                            'audio/aac', 'audio/amr', 'audio/ogg', 'video/mp4', 'video/3gpp'}
            attachment = msg.is_document or request.GET.get('download') == '1' or mime not in inline_types
            if mime not in inline_types and not msg.is_document:
                mime = 'application/octet-stream'
            response = FileResponse(storage.open(key, 'rb'), content_type=mime,
                as_attachment=attachment, filename=clean_filename(msg.display_filename or os.path.basename(key)))
            response['Cache-Control'] = 'private, no-store'
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        except (OSError, SuspiciousFileOperation):
            return None

    response = open_saved(value)
    if response is not None:
        return response
    media_id = msg.media_id or (value if value and '/' not in value and not value.startswith('private:') else '')
    if media_id:
        saved = WhatsAppService.telecharger_media_whatsapp(media_id, msg.media_type,
            msg.media_filename or msg.display_filename, msg.media_mime_type)
        if saved:
            msg.media_url = saved
            if saved.startswith('private:'):
                msg.media_size = private_storage().size(saved.removeprefix('private:'))
            msg.save(update_fields=['media_url', 'media_size'])
            response = open_saved(saved)
            if response is not None:
                return response
    raise Http404('Fichier WhatsApp indisponible. Le téléchargement peut être réessayé si Meta est temporairement inaccessible.')


@staff_required
@require_POST
def api_envoyer_reponse(request, pk):
    """Envoie une reponse directe via Meta WhatsApp Business."""
    get_object_or_404(ConversationWhatsApp, pk=pk)
    data = _json_body(request) if request.content_type == 'application/json' else request.POST
    if not isinstance(data, dict) and not hasattr(data, 'get'):
        return JsonResponse({'error': 'Requête invalide.'}, status=400)
    texte = (data.get("texte") or request.POST.get("texte", "")).strip()
    upload = request.FILES.get('fichier')
    if upload:
        try:
            result = WhatsAppService.envoyer_fichier_conversation(pk, upload, texte, request.user)
        except ValidationError as exc:
            return JsonResponse({'success': False, 'erreur': ' '.join(exc.messages)}, status=400)
        return JsonResponse(result, status=200 if result.get('success') else 502)
    if not texte:
        return JsonResponse({"error": "Le message ne peut pas etre vide."}, status=400)

    result = WhatsAppService.envoyer_message_conversation(pk, texte, auteur=request.user)
    if result.get("success"):
        return JsonResponse(result)
    return JsonResponse(result, status=500 if not settings.WHATSAPP_DRY_RUN else 200)


@staff_required
@require_POST
def api_generer_reponse_ia(request, pk):
    """Genere une suggestion de reponse IA ideale selon le fil du prospect."""
    suggestion = WhatsAppService.suggerer_reponse_ia(pk)
    return JsonResponse({"suggestion": suggestion})


@staff_required
@require_POST
def api_update_conversation_statut(request, pk):
    """Met a jour le statut, les notes ou convertit en prospect commercial."""
    conv = get_object_or_404(ConversationWhatsApp.objects.select_related("contact"), pk=pk)
    data = _json_body(request)

    statut = data.get("statut")
    priorite = data.get("priorite")
    notes = data.get("notes")
    convertir_commercial = data.get("convertir_commercial") in (True, "true", "1")

    fields = []
    if statut and statut in dict(ConversationWhatsApp.STATUTS):
        conv.statut = statut
        fields.append("statut")
    if priorite and priorite in dict(ConversationWhatsApp.PRIORITES):
        conv.priorite = priorite
        fields.append("priorite")
    if notes is not None:
        conv.notes = notes
        fields.append("notes")

    if convertir_commercial and not conv.commercial_prospect:
        from commercial_agent.models import ProspectBusiness
        prospect = ProspectBusiness.objects.create(
            nom=conv.contact.nom or f"Prospect WhatsApp {conv.contact.numero}",
            whatsapp=conv.contact.numero,
            telephone=conv.contact.numero,
            ville=conv.contact.ville or "",
            source=ProspectBusiness.Source.IMPORT,
            statut=ProspectBusiness.Statut.INTERESSE,
            description=f"Prospect WhatsApp converti depuis l'Inbox E-Shelle. Groupe: {conv.contact.groupe or 'N/A'}",
            notes=conv.notes,
            cree_par=request.user,
            assigne_a=request.user,
        )
        conv.commercial_prospect = prospect
        fields.append("commercial_prospect")

    if fields:
        conv.save(update_fields=fields + ["mis_a_jour_le"])

    return JsonResponse({
        "success": True,
        "statut": conv.statut,
        "priorite": conv.priorite,
        "commercial_prospect_id": conv.commercial_prospect_id,
        "commercial_prospect_nom": conv.commercial_prospect.nom if conv.commercial_prospect else "",
    })


@staff_required
@require_POST
def api_generer_variations(request):
    """Genere 5 variations IA du message pour eviter le spam et tester differents angles."""
    data = _json_body(request)
    segment = data.get("segment", "")
    contexte = data.get("contexte", "")
    variations = WhatsAppService.generer_variations_multiples_ia(segment, contexte, nb_variations=5)
    return JsonResponse({"variations": variations})


@staff_required
@require_POST
def api_simuler_message_entrant(request):
    """Simulateur de message entrant pour tests et demonstrations en local."""
    data = _json_body(request)
    numero = data.get("numero", "+237699000000")
    texte = data.get("texte", "Bonjour, je suis tres interesse par votre service E-Shelle ! Comment faire ?")
    profile_name = data.get("profile_name", "Jean Prospect")

    msg = WhatsAppService.enregistrer_message_entrant(
        numero=numero,
        texte=texte,
        whatsapp_msg_id=f"sim-{int(time.time()*1000)}",
        profile_name=profile_name,
    )
    if msg:
        return JsonResponse({
            "success": True,
            "conversation_id": msg.conversation_id,
            "contact_nom": msg.conversation.contact.nom,
            "message": msg.texte,
        })
    return JsonResponse({"error": "Erreur simulation."}, status=400)
