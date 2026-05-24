from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_GET

from billing.models import AffiliateProfile, Commission, Referral

from .models import BusinessLeadEvent, BusinessProfile, PaymentRequest, ProviderPlan
from .services import record_event_hit


@require_GET
def track(request, public_id):
    """Redirige vers WhatsApp/appel/detail en comptant le lead."""
    event = get_object_or_404(BusinessLeadEvent, public_id=public_id)
    target_url = record_event_hit(event, request=request)
    return redirect(target_url)


def provider_plans(request):
    """Page publique des abonnements prestataires."""
    plans = ProviderPlan.objects.filter(is_active=True).order_by("order", "monthly_price_xaf")
    return render(request, "business/provider_plans.html", {"plans": plans})


def partner(request):
    """Page publique pour recruter ambassadeurs et affiliés."""
    return render(request, "business/partner.html")


def commercial(request):
    """Page publique pour recruter des commerciaux terrain."""
    return render(request, "business/commercial.html")


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
    current = businesses.first()
    pending_requests = PaymentRequest.objects.filter(requested_by=request.user).select_related("business", "plan")[:8]
    return render(
        request,
        "business/dashboard.html",
        {
            "businesses": businesses,
            "current": current,
            "pending_requests": pending_requests,
            "plans": ProviderPlan.objects.filter(is_active=True).order_by("order"),
        },
    )


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
