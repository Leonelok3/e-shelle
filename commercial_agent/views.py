import csv
import json
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import CampagneProspection, ProspectBusiness, RelanceProspect, ScriptCommercial
from .services import CommercialAgentService
from . import sourcing_service


def staff_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


@staff_required
def dashboard(request):
    prospects = ProspectBusiness.objects.all()
    try:
        from whatsapp_agent.models import ContactWhatsApp

        contacts_whatsapp = ContactWhatsApp.objects.filter(consentement_confirme=True).count()
    except Exception:
        contacts_whatsapp = 0
    today = timezone.localdate()
    stats = {
        "total": prospects.count(),
        "contacts_whatsapp": contacts_whatsapp,
        "a_traiter": prospects.filter(Q(prochain_contact__isnull=True) | Q(prochain_contact__lte=today)).exclude(statut__in=["paye", "perdu"]).count(),
        "interesses": prospects.filter(statut__in=["interesse", "negociation"]).count(),
        "payes": prospects.filter(statut="paye").count(),
        "potentiel": prospects.exclude(statut__in=["paye", "perdu"]).aggregate(total=Sum("montant_potentiel_xaf"))["total"] or 0,
        "encaisse": prospects.filter(statut="paye").aggregate(total=Sum("montant_potentiel_xaf"))["total"] or 0,
    }
    due_prospects = prospects.filter(Q(prochain_contact__isnull=True) | Q(prochain_contact__lte=today)).exclude(statut__in=["paye", "perdu"]).order_by("-score")[:10]
    by_status = prospects.values("statut").annotate(total=Count("id")).order_by("-total")
    by_module = prospects.values("module").annotate(total=Count("id"), potentiel=Sum("montant_potentiel_xaf")).order_by("-potentiel")[:8]
    recent_relances = RelanceProspect.objects.select_related("prospect", "effectue_par").order_by("-cree_le")[:10]
    campaigns = CampagneProspection.objects.order_by("-cree_le")[:8]
    return render(
        request,
        "commercial_agent/dashboard.html",
        {
            "stats": stats,
            "due_prospects": due_prospects,
            "by_status": by_status,
            "by_module": by_module,
            "recent_relances": recent_relances,
            "campaigns": campaigns,
        },
    )


@staff_required
def prospect_list(request):
    prospects = ProspectBusiness.objects.select_related("business_profile", "assigne_a")
    status = request.GET.get("status", "")
    module = request.GET.get("module", "")
    q = request.GET.get("q", "")
    if status:
        prospects = prospects.filter(statut=status)
    if module:
        prospects = prospects.filter(module=module)
    if q:
        prospects = prospects.filter(
            Q(nom__icontains=q)
            | Q(ville__icontains=q)
            | Q(quartier__icontains=q)
            | Q(telephone__icontains=q)
            | Q(whatsapp__icontains=q)
        )
    paginator = Paginator(prospects.order_by("-score", "prochain_contact"), 30)
    page_obj = paginator.get_page(request.GET.get("page"))
    modules = ProspectBusiness.objects.exclude(module="").values_list("module", flat=True).distinct().order_by("module")
    return render(
        request,
        "commercial_agent/prospect_list.html",
        {
            "page_obj": page_obj,
            "statuts": ProspectBusiness.Statut.choices,
            "modules": modules,
            "filters": {"status": status, "module": module, "q": q},
        },
    )


@staff_required
def prospect_detail(request, pk):
    prospect = get_object_or_404(ProspectBusiness.objects.select_related("business_profile"), pk=pk)
    CommercialAgentService.refresh_prospect(prospect)
    message = CommercialAgentService.generate_message(prospect)
    return render(
        request,
        "commercial_agent/prospect_detail.html",
        {
            "prospect": prospect,
            "message": message,
            "whatsapp_url": CommercialAgentService.whatsapp_url(prospect, message),
            "relances": prospect.relances.select_related("effectue_par", "campagne")[:12],
            "statuts": ProspectBusiness.Statut.choices,
        },
    )


@staff_required
@require_POST
def generate_message(request, pk):
    prospect = get_object_or_404(ProspectBusiness, pk=pk)
    contexte = request.POST.get("contexte", "")
    message = CommercialAgentService.generate_message(prospect, contexte=contexte)
    messages.success(request, "Message IA regenere.")
    return render(
        request,
        "commercial_agent/prospect_detail.html",
        {
            "prospect": prospect,
            "message": message,
            "whatsapp_url": CommercialAgentService.whatsapp_url(prospect, message),
            "relances": prospect.relances.select_related("effectue_par", "campagne")[:12],
            "statuts": ProspectBusiness.Statut.choices,
        },
    )


@staff_required
@require_POST
def create_relance(request, pk):
    prospect = get_object_or_404(ProspectBusiness, pk=pk)
    message_text = request.POST.get("message", "")
    relance = CommercialAgentService.create_relance(prospect, user=request.user, message=message_text)
    messages.success(request, "Relance enregistree dans le pipeline.")
    wa_url = CommercialAgentService.whatsapp_url(prospect, relance.message)
    if wa_url:
        return redirect(wa_url)
    return redirect("commercial_agent:prospect_detail", pk=prospect.pk)


@staff_required
@require_POST
def update_status(request, pk):
    prospect = get_object_or_404(ProspectBusiness, pk=pk)
    statut = request.POST.get("statut")
    if statut in dict(ProspectBusiness.Statut.choices):
        prospect.statut = statut
        if statut == ProspectBusiness.Statut.PAYE:
            RelanceProspect.objects.create(
                prospect=prospect,
                type_action=RelanceProspect.TypeAction.PAIEMENT,
                resultat=RelanceProspect.Resultat.PAYE,
                montant_xaf=prospect.montant_potentiel_xaf,
                effectue_par=request.user,
                message="Prospect marque comme paye dans l'agent commercial.",
            )
        prospect.save(update_fields=["statut", "maj_le"])
        messages.success(request, "Statut mis a jour.")
    return redirect("commercial_agent:prospect_detail", pk=prospect.pk)


@staff_required
@require_POST
def sync_business(request):
    result = CommercialAgentService.sync_from_business_profiles(assigne_a=request.user)
    CommercialAgentService.seed_scripts()
    messages.success(request, f"Synchronisation terminee: {result['created']} crees, {result['updated']} mis a jour.")
    return redirect("commercial_agent:dashboard")


@staff_required
@require_POST
def sync_whatsapp_contacts(request):
    module = request.POST.get("module") or "services"
    limit = int(request.POST.get("limit") or 300)
    result = CommercialAgentService.sync_from_whatsapp_contacts(
        limit=limit,
        assigne_a=request.user,
        module=module,
    )
    messages.success(
        request,
        (
            "Contacts WhatsApp synchronises: "
            f"{result['created']} crees, {result['updated']} mis a jour, {result['skipped']} ignores."
        ),
    )
    return redirect("commercial_agent:dashboard")


@staff_required
@require_POST
def create_auto_campaign(request):
    name = request.POST.get("name") or f"Prospection E-Shelle {timezone.localdate().strftime('%d/%m/%Y')}"
    module = request.POST.get("module", "")
    ville = request.POST.get("ville", "")
    campagne = CommercialAgentService.create_campaign_from_due(name, user=request.user, module=module, ville=ville)
    messages.success(request, f"Campagne creee avec {campagne.prospects.count()} prospect(s).")
    return redirect("commercial_agent:dashboard")


@staff_required
@require_POST
def create_whatsapp_campaign(request):
    name = request.POST.get("name") or f"WhatsApp commercial E-Shelle {timezone.localdate().strftime('%d/%m/%Y')}"
    module = request.POST.get("module", "")
    ville = request.POST.get("ville", "")
    limit = int(request.POST.get("limit") or 50)
    campagne = CommercialAgentService.create_whatsapp_campaign_from_due(
        name,
        user=request.user,
        module=module,
        ville=ville,
        limit=limit,
    )
    messages.success(
        request,
        f"Campagne WhatsApp commerciale creee avec {campagne.total_destinataires} prospect(s). Verifie avant lancement.",
    )
    return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)


@staff_required
def sourcing_hub(request):
    """
    Cockpit de recherche et d'extraction de prestataires (restaurants à Douala, etc.).
    Permet la détection en direct, l'extraction de texte/posts, et l'action 1-clic WhatsApp/prospect.
    """
    mode = request.GET.get("mode") or request.POST.get("mode") or "verified"
    ville = request.GET.get("ville") or request.POST.get("ville") or "Douala"
    quartier = request.GET.get("quartier") or request.POST.get("quartier") or ""
    keyword = request.GET.get("keyword") or request.POST.get("keyword") or ""
    pasted_text = request.POST.get("pasted_text") or ""

    leads = []
    if request.method == "POST" and mode == "text" and pasted_text:
        leads = sourcing_service.extract_leads_from_text(pasted_text, default_ville=ville, default_quartier=quartier)
    elif mode == "auto":
        leads = sourcing_service.search_web_restaurants(ville=ville, quartier=quartier, keyword=keyword, limit=20)
    else:
        # Mode verified par défaut
        leads = sourcing_service.get_verified_douala_restaurants()
        if quartier:
            leads = [l for l in leads if quartier.lower() in (l.get("quartier") or "").lower()]
        if keyword:
            k = keyword.lower()
            leads = [l for l in leads if k in (l.get("nom") or "").lower() or k in (l.get("description") or "").lower()]

    # Enrichir chaque lead avec statut de doublon et URL WhatsApp
    enriched_leads = []
    for lead in leads:
        status_info = sourcing_service.check_lead_status(lead["telephone"], lead.get("nom", ""))
        whatsapp_url = sourcing_service.build_whatsapp_invite_url(
            lead["telephone"],
            lead.get("nom", "Restaurateur"),
            quartier=lead.get("quartier", ""),
            draft_resto_slug=status_info.get("resto_slug") or "",
        )
        lead_copy = dict(lead)
        lead_copy.update({
            "status_info": status_info,
            "whatsapp_url": whatsapp_url,
            "lead_json": json.dumps(lead),
        })
        enriched_leads.append(lead_copy)

    # Statistiques globales resto
    stats_resto = {
        "total_prospects_resto": ProspectBusiness.objects.filter(module="resto").count(),
        "total_restos_eshelle": 0,
        "nouveaux_trouves": len(enriched_leads),
    }
    try:
        from resto.models import Restaurant
        stats_resto["total_restos_eshelle"] = Restaurant.objects.count()
    except Exception:
        pass

    return render(
        request,
        "commercial_agent/sourcing_hub.html",
        {
            "mode": mode,
            "ville": ville,
            "quartier": quartier,
            "keyword": keyword,
            "pasted_text": pasted_text,
            "leads": enriched_leads,
            "leads_json": json.dumps(enriched_leads),
            "quartiers_douala": sourcing_service.DOUALA_QUARTIERS,
            "stats_resto": stats_resto,
        }
    )


@staff_required
@require_POST
def import_sourcing_lead(request):
    """Importe un lead individuel dans ProspectBusiness."""
    is_json = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json"
    
    if request.content_type == "application/json":
        data = json.loads(request.body.decode("utf-8"))
    else:
        data = {
            "nom": request.POST.get("nom"),
            "telephone": request.POST.get("telephone"),
            "whatsapp": request.POST.get("whatsapp"),
            "ville": request.POST.get("ville", "Douala"),
            "quartier": request.POST.get("quartier", ""),
            "description": request.POST.get("description", ""),
            "source": request.POST.get("source", "sourcing_web"),
        }

    try:
        prospect, created = sourcing_service.save_lead_as_prospect(data, user=request.user)
        msg = f"Prospect '{prospect.nom}' {'créé' if created else 'mis à jour'} avec succès."
        if is_json:
            return JsonResponse({
                "ok": True,
                "message": msg,
                "created": created,
                "prospect_id": prospect.pk,
                "detail_url": f"/commercial-agent/prospects/{prospect.pk}/",
            })
        messages.success(request, msg)
    except Exception as e:
        if is_json:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
        messages.error(request, f"Erreur lors de l'import: {e}")

    return redirect(request.META.get("HTTP_REFERER") or "commercial_agent:sourcing_hub")


@staff_required
@require_POST
def import_sourcing_bulk(request):
    """Importe une liste complète de leads en une seule opération."""
    try:
        leads_raw = request.POST.get("leads_json") or "[]"
        leads_list = json.loads(leads_raw)
        
        created_count = 0
        updated_count = 0
        for lead in leads_list:
            clean_p = sourcing_service.clean_cameroon_phone(lead.get("telephone"))
            if clean_p:
                _, created = sourcing_service.save_lead_as_prospect(lead, user=request.user)
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
        messages.success(
            request,
            f"Importation terminée : {created_count} nouveau(x) prospect(s) créé(s), {updated_count} mis à jour."
        )
    except Exception as e:
        messages.error(request, f"Erreur lors de l'import en masse : {e}")

    return redirect("commercial_agent:prospect_list")


@staff_required
@require_POST
def create_resto_draft_view(request):
    """Pré-crée une fiche vitrine Restaurant sur E-Shelle Resto pour faciliter le closing."""
    is_json = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json"
    
    lead_data = {
        "nom": request.POST.get("nom"),
        "telephone": request.POST.get("telephone"),
        "whatsapp": request.POST.get("whatsapp"),
        "ville": request.POST.get("ville", "Douala"),
        "quartier": request.POST.get("quartier", ""),
        "description": request.POST.get("description", ""),
    }

    try:
        resto = sourcing_service.create_resto_draft(lead_data, user=request.user)
        # Met également à jour le prospect s'il existe
        prospect, _ = sourcing_service.save_lead_as_prospect(lead_data, user=request.user)
        
        # Mettre à jour le message d'invitation avec le lien direct
        whatsapp_url = sourcing_service.build_whatsapp_invite_url(
            lead_data["telephone"],
            resto.name,
            quartier=lead_data["quartier"],
            draft_resto_slug=resto.slug,
        )
        
        resto_url = f"/resto/{resto.slug}/"
        msg = f"Fiche restaurant '{resto.name}' pré-créée ! Lien vitrine : {resto_url}"
        
        if is_json:
            return JsonResponse({
                "ok": True,
                "resto_id": resto.pk,
                "resto_slug": resto.slug,
                "resto_url": resto_url,
                "whatsapp_url": whatsapp_url,
                "message": msg,
            })
        messages.success(request, msg)
    except Exception as e:
        if is_json:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
        messages.error(request, f"Erreur de création de la fiche resto : {e}")

    return redirect(request.META.get("HTTP_REFERER") or "commercial_agent:sourcing_hub")


@staff_required
def export_sourcing_csv(request):
    """Exporte la sélection de leads sous forme de tableur CSV prêt pour Excel ou Google Sheets."""
    mode = request.GET.get("mode") or "verified"
    ville = request.GET.get("ville") or "Douala"
    quartier = request.GET.get("quartier") or ""

    if mode == "auto":
        leads = sourcing_service.search_web_restaurants(ville=ville, quartier=quartier, limit=50)
    else:
        leads = sourcing_service.get_verified_douala_restaurants()
        if quartier:
            leads = [l for l in leads if quartier.lower() in (l.get("quartier") or "").lower()]

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    filename = f"leads_resto_{ville.lower()}_{timezone.localdate().strftime('%Y%m%d')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Nom Établissement", "Numéro Normalisé", "Affichage", "Opérateur",
        "Ville", "Quartier", "Spécialités", "Lien WhatsApp Direct", "Source"
    ])

    for lead in leads:
        wa_url = sourcing_service.build_whatsapp_invite_url(
            lead["telephone"],
            lead.get("nom", ""),
            quartier=lead.get("quartier", "")
        )
        writer.writerow([
            lead.get("nom", ""),
            lead.get("telephone", ""),
            lead.get("formatted_phone", ""),
            lead.get("operateur", ""),
            lead.get("ville", ville),
            lead.get("quartier", ""),
            ", ".join(lead.get("specialites", [])),
            wa_url,
            lead.get("source", ""),
        ])

    return response

