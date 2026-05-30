import csv
import json

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

from .forms import CampagneForm
from .models import Campagne, MessageEnvoi
from .services import AI_PRESETS, WhatsAppService
from .tasks import lancer_campagne_task, recalculer_stats_campagne


def staff_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def _creer_messages_campagne(campagne):
    """Prepare les lignes MessageEnvoi selon les filtres de la campagne."""

    contacts = WhatsAppService.recuperer_contacts(
        campagne.filtre_role,
        campagne.filtre_ville,
        campagne.filtre_date_inscription_depuis,
    )
    campagne.messages.all().delete()
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
    lancer_campagne_task.delay(campagne.pk)
    if settings.WHATSAPP_DRY_RUN:
        messages.success(request, "Simulation lancee: aucun message reel ne sera envoye a Meta.")
    else:
        messages.success(request, "Lancement reel de la campagne programme.")
    return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)


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
