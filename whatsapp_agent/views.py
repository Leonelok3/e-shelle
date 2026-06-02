import csv
import json
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import CampagneForm
from .models import Campagne, ContactWhatsApp, MessageEnvoi
from .services import AI_PRESETS, WhatsAppService
from .tasks import lancer_campagne_direct, lancer_campagne_task, recalculer_stats_campagne


def staff_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


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
    contacts_whatsapp = campagne.destinataires_contacts.all().order_by("nom", "numero")
    if contacts_whatsapp.exists():
        batch = []
        for contact in contacts_whatsapp:
            batch.append(
                MessageEnvoi(
                    campagne=campagne,
                    destinataire_nom=contact.nom or f"Contact WhatsApp {contact.numero}",
                    numero_whatsapp=contact.numero,
                    message_final=_personnaliser_message_contact(campagne.message_template, contact),
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
    for user in contacts:
        batch.append(
            MessageEnvoi(
                campagne=campagne,
                user=user,
                numero_whatsapp=user.whatsapp,
                message_final=WhatsAppService.personnaliser_message(campagne.message_template, user),
            )
        )
    MessageEnvoi.objects.bulk_create(batch, batch_size=500)
    recalculer_stats_campagne(campagne)


def _personnaliser_message_contact(template, contact):
    """Personnalise un message pour un contact WhatsApp importe."""

    nom = (contact.nom or "").strip()
    prenom = nom.split()[0] if nom else "Contact"
    return (
        template.replace("{{prenom}}", prenom)
        .replace("{{nom}}", nom or prenom)
        .replace("{{ville}}", (contact.ville or "").strip())
        .replace("{{numero}}", contact.numero)
    )


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
    total_autorises = ContactWhatsApp.objects.filter(consentement_confirme=True).count()

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
    """Cree une campagne depuis une selection manuelle de contacts WhatsApp."""

    contact_ids = request.POST.getlist("contacts")
    contacts = ContactWhatsApp.objects.filter(id__in=contact_ids, consentement_confirme=True)
    if not contact_ids or not contacts.exists():
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
                    if not contact.consentement_confirme:
                        contact.consentement_confirme = True
                        changed = True
                    if changed:
                        contact.save(update_fields=["ville", "groupe", "note", "consentement_confirme", "mis_a_jour_le"])
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
        if form.is_valid():
            campagne = form.save(commit=False)
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

    return render(
        request,
        "whatsapp_agent/creer_campagne.html",
        {
            "form": form,
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
    if settings.WHATSAPP_DRY_RUN:
        lancer_campagne_direct(campagne.pk)
        messages.success(request, "Simulation terminee: les messages ont ete marques comme envoyes sans appel Meta.")
    else:
        try:
            lancer_campagne_task.delay(campagne.pk)
            messages.success(request, "Lancement reel de la campagne programme.")
        except Exception as exc:
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
    if not numero_test:
        messages.warning(request, "Entre ton numero WhatsApp de test avant l'envoi.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)

    exemple = campagne.messages.order_by("id").first()
    if not exemple:
        messages.warning(request, "Aucun message prepare dans cette campagne.")
        return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)

    message_test = (
        "[TEST E-SHELLE]\n"
        f"Campagne: {campagne.nom}\n\n"
        f"{exemple.message_final}"
    )
    result = WhatsAppService.envoyer_message(numero_test, message_test)
    if result["success"]:
        if settings.WHATSAPP_DRY_RUN:
            messages.success(
                request,
                f"Test simule avec succes vers {numero_test}. Active Meta pour recevoir le message reel.",
            )
        else:
            messages.success(request, f"Message test envoye vers {numero_test}.")
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
    """API AJAX qui genere un message marketing avec Claude."""

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

    consentement = data.get("consentement_confirme", data.get("consent", True))
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
        if not contact.consentement_confirme:
            contact.consentement_confirme = True
            updated = True
        if updated:
            contact.save(update_fields=["nom", "ville", "groupe", "source", "note", "consentement_confirme", "mis_a_jour_le"])
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
    """Webhook Meta: verification GET puis reception des statuts POST."""

    if request.method == "GET":
        verify_token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if verify_token == settings.WHATSAPP_VERIFY_TOKEN and challenge:
            return HttpResponse(challenge)
        return HttpResponse("Token invalide", status=403)

    if request.method != "POST":
        return HttpResponse(status=405)

    data = _json_body(request)
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status in value.get("statuses", []):
                message_id = status.get("id", "")
                wa_status = status.get("status", "")
                nouveau_statut = {"sent": "envoye", "delivered": "livre", "read": "lu", "failed": "echec"}.get(wa_status)
                if message_id and nouveau_statut:
                    update_data = {"statut": nouveau_statut, "mis_a_jour_le": timezone.now()}
                    if nouveau_statut == "echec":
                        update_data["erreur"] = str(status.get("errors", ""))
                    MessageEnvoi.objects.filter(whatsapp_message_id=message_id).update(**update_data)
                    for campagne in Campagne.objects.filter(messages__whatsapp_message_id=message_id).distinct():
                        recalculer_stats_campagne(campagne)

    return JsonResponse({"status": "ok"})
