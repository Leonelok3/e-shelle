import urllib.parse

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Count, F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_GET

from billing.models import AffiliateProfile, Commission, Referral

from .models import BusinessLeadEvent, BusinessProfile, HomeAdSlide, PaymentRequest, PremiumSectorCampaign, ProviderPlan
from .reporting import business_report_context, render_business_report_pdf
from .services import collect_business_items, create_tracking_event, record_event_hit


@require_GET
def track(request, public_id):
    """Redirige vers WhatsApp/appel/detail en comptant le lead."""
    event = get_object_or_404(BusinessLeadEvent, public_id=public_id)
    target_url = record_event_hit(event, request=request)
    return redirect(target_url)


@require_GET
def go_business(request, business_id, event_type):
    """Clic public depuis la home: compte le lead puis redirige."""
    business = get_object_or_404(BusinessProfile, pk=business_id, is_active=True)
    allowed = {
        "view": BusinessLeadEvent.EventType.VIEW,
        "whatsapp": BusinessLeadEvent.EventType.WHATSAPP,
        "detail": BusinessLeadEvent.EventType.DETAIL,
        "order": BusinessLeadEvent.EventType.ORDER,
    }
    event_kind = allowed.get(event_type, BusinessLeadEvent.EventType.DETAIL)
    target_url = _business_public_target(business, event_kind)
    if event_kind != BusinessLeadEvent.EventType.VIEW:
        BusinessProfile.objects.filter(pk=business.pk).update(views_count=F("views_count") + 1)
    event = create_tracking_event(business, event_kind, target_url, source="home")
    return redirect(record_event_hit(event, request=request))


@require_GET
def go_slide(request, slide_id):
    """Clic sur un slide publicitaire de la home."""
    slide = get_object_or_404(HomeAdSlide.objects.select_related("business"), pk=slide_id, is_active=True)
    target_url = slide.destination_url()
    HomeAdSlide.objects.filter(pk=slide.pk).update(clicks_count=F("clicks_count") + 1)
    if slide.business:
        BusinessProfile.objects.filter(pk=slide.business_id).update(views_count=F("views_count") + 1)
        event = create_tracking_event(
            slide.business,
            BusinessLeadEvent.EventType.ORDER,
            target_url,
            source="home_slide",
            metadata={"slide_id": slide.pk, "slide_title": slide.title},
        )
        target_url = record_event_hit(event, request=request)
    return redirect(target_url)


def _business_public_target(business, event_kind):
    if event_kind in {BusinessLeadEvent.EventType.WHATSAPP, BusinessLeadEvent.EventType.ORDER}:
        number = (business.whatsapp or business.phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if number:
            if not number.startswith("237"):
                number = f"237{number}"
            import urllib.parse
            text = urllib.parse.quote(f"Bonjour {business.name}, je viens de E-Shelle.")
            return f"https://wa.me/{number}?text={text}"
    if business.promo_url:
        return business.promo_url
    import urllib.parse
    return f"/chat/?q={urllib.parse.quote(f'Je veux contacter {business.name}')}"


def public_profile(request, public_slug):
    """Vitrine publique centrale d'une activite E-Shelle."""
    business = get_object_or_404(BusinessProfile, public_slug=public_slug, is_active=True)
    BusinessProfile.objects.filter(pk=business.pk).update(views_count=F("views_count") + 1)
    source_object = business.content_object
    source_url = ""
    if source_object and hasattr(source_object, "get_absolute_url"):
        try:
            source_url = source_object.get_absolute_url()
        except Exception:
            source_url = ""
    public_url = request.build_absolute_uri(business.get_absolute_url())
    share_text = f"Decouvrez {business.name} sur E-Shelle: {public_url}"
    whatsapp_url = business.whatsapp_url(f"Bonjour {business.name}, je viens de votre boutique E-Shelle: {public_url}")
    return render(
        request,
        "business/public_profile.html",
        {
            "business": business,
            "source_object": source_object,
            "source_url": source_url,
            "items": collect_business_items(business),
            "public_url": public_url,
            "share_text": share_text,
            "share_whatsapp_url": f"https://wa.me/?text={urllib.parse.quote(share_text)}",
            "whatsapp_url": whatsapp_url,
        },
    )


def provider_plans(request):
    """Page publique des abonnements prestataires."""
    plans = ProviderPlan.objects.filter(is_active=True).order_by("order", "monthly_price_xaf")
    proof = {
        "premium_businesses": BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        ).count(),
        "views": BusinessProfile.objects.aggregate(total=Sum("views_count"))["total"] or 0,
        "leads": BusinessProfile.objects.aggregate(total=Sum("leads_count"))["total"] or 0,
    }
    return render(request, "business/provider_plans.html", {"plans": plans, "proof": proof})


def solutions(request):
    """Page commerciale qui oriente chaque besoin vers la bonne application E-Shelle."""
    proof = {
        "premium_businesses": BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        ).count(),
        "views": BusinessProfile.objects.aggregate(total=Sum("views_count"))["total"] or 0,
        "leads": BusinessProfile.objects.aggregate(total=Sum("leads_count"))["total"] or 0,
    }
    solutions_grid = [
        {
            "title": "Je veux plus de clients",
            "tag": "Visibilité",
            "desc": "Fiche business, WhatsApp, mise en avant locale, statistiques et carrousel premium.",
            "url": "/business/plans/",
            "cta": "Devenir Premium",
            "accent": "#7ee56f",
        },
        {
            "title": "Je veux vendre mes produits",
            "tag": "Marketplace",
            "desc": "Publiez produits, services, véhicules, biens immobiliers ou produits santé avec lien partageable.",
            "url": "/annonces/",
            "cta": "Voir la marketplace",
            "accent": "#f28a19",
        },
        {
            "title": "Je veux créer une pub",
            "tag": "IA Marketing",
            "desc": "AdGen génère titres, posts Facebook/Instagram, messages WhatsApp et scripts vidéo.",
            "url": "/pub/",
            "cta": "Ouvrir AdGen",
            "accent": "#8b5cf6",
        },
        {
            "title": "Je gère une tontine ou réunion",
            "tag": "Association",
            "desc": "Njangi Digital suit membres, cotisations, mains, prêts, fonds communs et rapports PDF.",
            "url": "/njangi/",
            "cta": "Voir Njangi",
            "accent": "#38bdf8",
        },
        {
            "title": "Je fais de la collecte terrain",
            "tag": "Microfinance",
            "desc": "Tchaslucpay suit collecteurs, clients, dépôts, retraits, reçus PDF et soldes.",
            "url": "http://127.0.0.1:8001/",
            "cta": "Voir la collecte",
            "accent": "#10b981",
        },
        {
            "title": "Je cherche un artisan fiable",
            "tag": "Travaux",
            "desc": "Plombiers, électriciens, maçons, carreleurs, peintres et menuisiers proches du client.",
            "url": "/artisans/",
            "cta": "Voir artisans",
            "accent": "#facc15",
        },
    ]
    demos = [
        ("Santé", "/sante/produits/", "Produits santé avec photos et commande WhatsApp"),
        ("Immobilier", "/immobilier/", "Biens, agences et vitrines publiques"),
        ("Auto", "/auto/", "Vente et location de véhicules"),
        ("Artisans", "/artisans/", "Profils artisans et demandes travaux"),
        ("Njangi", "/njangi/groupe/reunion-demo-e-shelle/", "Réunion/tontine démo"),
        ("Collecte", "http://127.0.0.1:8001/", "Collecte terrain et reçus PDF"),
        ("AdGen", "/pub/", "Publicités IA pour business"),
    ]
    return render(
        request,
        "business/solutions.html",
        {"solutions": solutions_grid, "demos": demos, "proof": proof},
    )


def custom_app_offer(request):
    """Offre application personnalisee hebergee sur domaine client."""
    whatsapp_text = urllib.parse.quote(
        "Bonjour E-Shelle, je veux une application personnalisee pour mon business avec hebergement sur mon domaine."
    )
    return render(
        request,
        "business/custom_app_offer.html",
        {"whatsapp_url": f"https://wa.me/237680625082?text={whatsapp_text}"},
    )


def partner(request):
    """Page publique pour recruter ambassadeurs et affiliés."""
    return render(request, "business/partner.html")


def commercial(request):
    """Page publique pour recruter des commerciaux terrain."""
    return render(request, "business/commercial.html")


@staff_member_required
def commercial_admin_dashboard(request):
    """Dashboard staff pour suivre prospects, secteurs et campagnes premium."""
    selected_module = request.GET.get("module", "").strip()
    selected_status = request.GET.get("status", "").strip()
    days = _positive_int(request.GET.get("days"), 30)
    since = timezone.now() - timezone.timedelta(days=days)

    businesses = BusinessProfile.objects.order_by("-created_at")
    if selected_module:
        businesses = businesses.filter(module=selected_module)

    payment_requests = PaymentRequest.objects.select_related("business", "plan", "requested_by").order_by("-created_at")
    if selected_status:
        payment_requests = payment_requests.filter(status=selected_status)

    campaigns = PremiumSectorCampaign.objects.order_by("-starts_at")
    if selected_module:
        campaigns = campaigns.filter(module=selected_module)
    campaigns = campaigns[:12]

    module_pipeline = (
        businesses.values("module")
        .annotate(
            total=Count("id"),
            premium=Count("id", filter=models.Q(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM])),
            leads=Sum("leads_count"),
            views=Sum("views_count"),
        )
        .order_by("-total")
    )
    recent_leads = BusinessLeadEvent.objects.select_related("business").filter(created_at__gte=since).order_by("-created_at")
    if selected_module:
        recent_leads = recent_leads.filter(business__module=selected_module)
    recent_leads = recent_leads[:20]

    funnel = {
        "visitors": max(BusinessLeadEvent.objects.filter(created_at__gte=since, event_type=BusinessLeadEvent.EventType.VIEW).count(), 1),
        "contacts": BusinessLeadEvent.objects.filter(
            created_at__gte=since,
            event_type__in=[BusinessLeadEvent.EventType.WHATSAPP, BusinessLeadEvent.EventType.PHONE, BusinessLeadEvent.EventType.ORDER],
        ).count(),
        "requests": payment_requests.filter(created_at__gte=since).count(),
        "premium": businesses.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]).count(),
    }
    funnel["contacts_pct"] = round((funnel["contacts"] / funnel["visitors"]) * 100, 1)
    funnel["requests_pct"] = round((funnel["requests"] / funnel["visitors"]) * 100, 1)
    funnel["premium_pct"] = round((funnel["premium"] / max(businesses.count(), 1)) * 100, 1)

    context = {
        "total_businesses": businesses.count(),
        "premium_businesses": businesses.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]).count(),
        "pending_payments": payment_requests.filter(status=PaymentRequest.Status.PENDING).count(),
        "total_leads": businesses.aggregate(total=Sum("leads_count"))["total"] or 0,
        "module_pipeline": module_pipeline,
        "payment_requests": payment_requests[:12],
        "campaigns": campaigns,
        "recent_leads": recent_leads,
        "funnel": funnel,
        "filters": {"module": selected_module, "status": selected_status, "days": days},
        "modules": BusinessProfile.Module.choices,
        "statuses": PaymentRequest.Status.choices,
    }
    return render(request, "business/commercial_admin_dashboard.html", context)


@login_required
def partner_dashboard(request):
    """Dashboard partenaire: lien, clics, inscrits, conversions, commissions."""
    profile, _ = AffiliateProfile.objects.get_or_create(user=request.user)
    referral_path = f"/ref/{profile.ref_code}/"
    referral_link = request.build_absolute_uri(referral_path)

    referrals = Referral.objects.filter(affiliate=profile).select_related("referred_user")
    referred_user_ids = list(referrals.values_list("referred_user_id", flat=True))
    converted_businesses = 0
    if referred_user_ids:
        from .models import BusinessProfile
        converted_businesses = BusinessProfile.objects.filter(owner_id__in=referred_user_ids).count()

    commissions = Commission.objects.filter(affiliate=profile)
    pending_amount = commissions.filter(status="PENDING").aggregate(total=Sum("amount"))["total"] or 0
    paid_amount = commissions.filter(status="PAID").aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "profile": profile,
        "referral_link": referral_link,
        "referrals_count": referrals.count(),
        "converted_businesses": converted_businesses,
        "pending_amount": pending_amount,
        "paid_amount": paid_amount,
        "balance_amount": pending_amount,
        "commissions": commissions.order_by("-created_at")[:20],
    }
    return render(request, "business/partner_dashboard.html", context)


@login_required
def onboarding(request):
    """Creation rapide d'une fiche business adaptee au terrain."""
    selected_plan = request.GET.get("plan") or request.POST.get("plan") or request.session.get("business_selected_plan", "free")
    plan = ProviderPlan.objects.filter(code=selected_plan, is_active=True).first() or ProviderPlan.objects.filter(code="free").first()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        module = request.POST.get("module", BusinessProfile.Module.GENERAL)
        city = request.POST.get("city", "").strip()
        district = request.POST.get("district", "").strip()
        phone = request.POST.get("phone", "").strip()
        whatsapp = request.POST.get("whatsapp", "").strip()
        description = request.POST.get("description", "").strip()

        if not name or not phone:
            messages.error(request, "Le nom du business et le telephone sont obligatoires.")
        else:
            business = BusinessProfile.objects.create(
                owner=request.user,
                module=module if module in dict(BusinessProfile.Module.choices) else BusinessProfile.Module.GENERAL,
                name=name,
                city=city,
                district=district,
                phone=phone,
                whatsapp=whatsapp or phone,
                description=description,
                plan=BusinessProfile.Plan.FREE,
                is_active=True,
            )
            request.session["current_business_id"] = business.id
            request.session.modified = True
            messages.success(request, "Votre fiche business a ete creee. Choisissez maintenant comment activer votre plan.")
            if plan and plan.code != "free":
                return redirect(f"/business/payment/request/{business.id}/?plan={plan.code}")
            return redirect("business:dashboard")

    return render(
        request,
        "business/onboarding.html",
        {
            "plan": plan,
            "modules": BusinessProfile.Module.choices,
        },
    )


@login_required
def dashboard(request):
    businesses = BusinessProfile.objects.filter(owner=request.user).order_by("-updated_at")
    current_id = request.GET.get("business")
    current = businesses.filter(pk=current_id).first() if current_id else businesses.first()
    days = _positive_int(request.GET.get("days"), 30)
    since = timezone.now() - timezone.timedelta(days=days)
    pending_requests = PaymentRequest.objects.filter(requested_by=request.user).select_related("business", "plan")[:8]
    recent_events = []
    event_stats = []
    chart_stats = []
    marketing_pack = None
    public_url = ""
    share_whatsapp_url = ""
    whatsapp_url = ""
    if current:
        public_url = request.build_absolute_uri(current.get_absolute_url())
        share_text = f"Decouvrez {current.name} sur E-Shelle: {public_url}"
        share_whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(share_text)}"
        whatsapp_url = current.whatsapp_url(f"Bonjour {current.name}, je viens de votre boutique E-Shelle: {public_url}")
        filtered_events = current.lead_events.filter(created_at__gte=since)
        recent_events = filtered_events.order_by("-created_at")[:12]
        event_stats = (
            filtered_events.values("event_type")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        chart_stats = _event_chart_stats(event_stats)
        marketing_pack = _build_marketing_pack(current)
    return render(
        request,
        "business/dashboard.html",
        {
            "businesses": businesses,
            "current": current,
            "pending_requests": pending_requests,
            "plans": ProviderPlan.objects.filter(is_active=True).order_by("order"),
            "recent_events": recent_events,
            "event_stats": event_stats,
            "chart_stats": chart_stats,
            "marketing_pack": marketing_pack,
            "public_url": public_url,
            "share_whatsapp_url": share_whatsapp_url,
            "whatsapp_url": whatsapp_url,
            "filters": {"days": days, "business": current.id if current else ""},
        },
    )


@login_required
def performance_report(request, business_id):
    """Rapport prestataire imprimable/partageable."""
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    days = _positive_int(request.GET.get("days"), 30)
    since = timezone.now() - timezone.timedelta(days=days)
    report_context = business_report_context(business, days)
    filtered_events = report_context["events"]
    events = filtered_events.order_by("-created_at")[:80]
    event_stats = filtered_events.values("event_type").annotate(total=Count("id")).order_by("-total")
    chart_stats = _event_chart_stats(event_stats)
    report_text = report_context["summary"]
    import urllib.parse
    whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(report_text)}"
    return render(
        request,
        "business/performance_report.html",
        {
            "business": business,
            "events": events,
            "event_stats": event_stats,
            "chart_stats": chart_stats,
            "report_text": report_text,
            "whatsapp_url": whatsapp_url,
            "days": days,
        },
    )


@login_required
def performance_report_pdf(request, business_id):
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    days = _positive_int(request.GET.get("days"), 30)
    report_context = business_report_context(business, days)
    pdf = render_business_report_pdf(business, report_context)
    filename = f"rapport-e-shelle-{business.slug or business.id}-{days}j.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _event_chart_stats(event_stats):
    rows = list(event_stats)
    max_total = max([row["total"] for row in rows] or [1])
    return [
        {
            "label": row["event_type"],
            "total": row["total"],
            "percent": max(6, round((row["total"] / max_total) * 100)),
        }
        for row in rows
    ]


def _positive_int(value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number in {7, 30, 90, 365} else default


def _build_marketing_pack(business):
    offer = business.promo_offer or "une offre spéciale disponible aujourd'hui"
    location = ", ".join(part for part in [business.city, business.district] if part)
    location_text = f" à {location}" if location else ""
    name = business.name
    module = business.get_module_display()
    whatsapp = (
        f"Bonjour, profitez de {offer} chez {name}{location_text}. "
        "Répondez à ce message pour réserver ou commander via E-Shelle."
    )
    facebook = (
        f"{name} vous accueille{location_text}. {offer}. "
        f"Service {module}, contact rapide, visibilité E-Shelle et réponse directe sur WhatsApp."
    )
    status = f"{name} · {offer} · Commandez maintenant sur E-Shelle."
    carousel = [
        business.promo_headline or f"Découvrez {name}",
        offer,
        f"Disponible{location_text}",
        "Contact rapide via E-Shelle AI",
    ]
    return {
        "whatsapp": whatsapp,
        "facebook": facebook,
        "status": status,
        "carousel": carousel,
        "image_prompt": (
            f"Professional premium advertising visual for {name}, {module}, Cameroon market, "
            f"highlighting: {offer}. Clean modern layout, product/service in focus."
        ),
    }


@login_required
def payment_request(request, business_id):
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    plan_code = request.GET.get("plan") or request.POST.get("plan") or "business"
    plan = get_object_or_404(ProviderPlan, code=plan_code, is_active=True)

    if request.method == "POST":
        method = request.POST.get("method", PaymentRequest.Method.CASH_ON_DELIVERY)
        phone = request.POST.get("phone", business.whatsapp or business.phone)
        note = request.POST.get("note", "").strip()
        payment = PaymentRequest.objects.create(
            business=business,
            plan=plan,
            requested_by=request.user,
            method=method if method in dict(PaymentRequest.Method.choices) else PaymentRequest.Method.CASH_ON_DELIVERY,
            amount_xaf=plan.monthly_price_xaf,
            phone=phone,
            note=note,
        )
        messages.success(request, "Demande envoyee. L'equipe E-Shelle vous contactera pour confirmer le paiement.")
        return redirect("business:payment_success", pk=payment.pk)

    return render(
        request,
        "business/payment_request.html",
        {
            "business": business,
            "plan": plan,
            "methods": PaymentRequest.Method.choices,
        },
    )


@login_required
def payment_success(request, pk):
    payment = get_object_or_404(PaymentRequest, pk=pk, requested_by=request.user)
    whatsapp_number = "237680625082"
    whatsapp_text = (
        f"Bonjour E-Shelle, j'ai envoye une demande d'activation pour {payment.business.name}. "
        f"Plan: {payment.plan.name}. Montant: {payment.amount_xaf} FCFA. "
        f"Reference demande: #{payment.pk}."
    )
    import urllib.parse
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(whatsapp_text)}"
    return render(
        request,
        "business/payment_success.html",
        {
            "payment": payment,
            "whatsapp_url": whatsapp_url,
        },
    )

# Create your views here.
