from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import CampagneProspection, ProspectBusiness, RelanceProspect, ScriptCommercial
from .services import CommercialAgentService


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
