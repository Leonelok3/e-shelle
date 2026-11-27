"""A business's measurable progress and consented partner follow-up."""

from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from billing.models import AffiliateProfile, Commission, Referral
from dashboard.models import Notification
from immobilier_cameroun.agency import is_estate_agency, public_agency_properties
from immobilier_cameroun.models import StatutVisite
from salonhub.bookings.models import Appointment
from whatsapp_commerce.activation import connection_blockers
from whatsapp_commerce.checkout import verified_order_payment
from whatsapp_commerce.models import BusinessWhatsAppBooking, BusinessWhatsAppConnection, WhatsAppDraftOrder, WhatsAppOfferClick

from .models import BusinessProfile, ProviderPlan
from .services import provider_subscription_payments


def _paid(business_id):
    return WhatsAppDraftOrder.objects.filter(
        business_id=business_id, contact__business_id=business_id, status=WhatsAppDraftOrder.Status.CONFIRMED,
        boutique_order__business_profile_id=business_id, payment_transaction__commande_id=F("boutique_order__pk"),
    ).exclude(boutique_order__statut__in=["annulee", "remboursee"]).filter(verified_order_payment())


def _appointments(business_id):
    return BusinessWhatsAppBooking.objects.filter(
        contact__business_id=business_id, appointment__status__in=[Appointment.Status.CONFIRMED, Appointment.Status.DONE],
    ).filter(Q(property_visit__isnull=True) | Q(property_visit__bien__agence_id=business_id, property_visit__statut=StatutVisite.CONFIRME))


def renewal_plan(business):
    plans = ProviderPlan.objects.filter(is_active=True, monthly_price_xaf__gt=0).exclude(plan_level=BusinessProfile.Plan.FREE)
    previous = provider_subscription_payments(business).order_by("-created_at", "-pk").first()
    if previous and (business.plan == BusinessProfile.Plan.FREE or not business.subscription_active):
        return plans.filter(code=(previous.metadata or {}).get("provider_plan")).first()
    same_level = plans.filter(plan_level=business.plan)
    if previous:
        exact = same_level.filter(code=(previous.metadata or {}).get("provider_plan")).first()
        if exact:
            return exact
    return same_level.first()


def _next_action(business, connection, clicks, conversations, paid, bookings):
    agents = reverse("whatsapp_commerce:agent_center", args=[business.pk])
    if business.plan not in {BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM}:
        return "Compléter la fiche", reverse("business:business_edit", args=[business.pk]), "Vérifie les coordonnées, les horaires et les informations publiques de ta fiche."
    if not business.is_published or connection_blockers(connection) or not connection.agent_enabled:
        return "Continuer la mise en route", agents, "Vérifie la fiche, le numéro et le test WhatsApp de cette entreprise."
    inventory = public_agency_properties(business) if is_estate_agency(business) else business.catalog_items.filter(is_active=True)
    if not inventory.exists():
        return "Publier la première offre", agents, "Ajoute une offre disponible pour donner au client un point de départ."
    if not clicks or not conversations:
        return "Partager une offre", reverse("whatsapp_commerce:offer_report", args=[business.pk]), "Choisis une offre et partage son lien pour ouvrir les premières conversations."
    if not paid and not bookings:
        return "Vérifier les conversations", reverse("whatsapp_commerce:business_dashboard", args=[business.pk]) + "#conversation", "Repère ce qui bloque le paiement ou la confirmation d’un créneau."
    return "Voir les offres qui génèrent des résultats", reverse("whatsapp_commerce:offer_report", args=[business.pk]), "Compare les résultats par offre pour décider laquelle partager ensuite."


@login_required
@require_GET
@never_cache
def business_progress(request, business_id):
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    now = timezone.now()
    since = now - timedelta(days=30)
    clicks = WhatsAppOfferClick.objects.filter(connection__business=business, created_at__gte=since)
    conversations = clicks.filter(entry_message__contact__business=business).values("entry_message__contact_id").distinct().count()
    click_count = clicks.count()
    paid = _paid(business.pk).filter(confirmed_at__gte=since, confirmed_at__lte=now)
    sales_count = paid.count()
    bookings_count = _appointments(business.pk).filter(appointment__created_at__gte=since).count()
    turnover = paid.order_by().values("payment_transaction__devise").annotate(total=Sum("payment_transaction__montant"))
    connection = BusinessWhatsAppConnection.objects.filter(business=business).first()
    plan = renewal_plan(business)
    affiliate = Referral.objects.filter(referred_user=request.user, affiliate__is_enabled=True, affiliate__user__is_active=True).first()
    return render(request, "business/business_progress.html", {
        "business": business, "since": since, "today": now, "clicks": click_count, "conversations": conversations,
        "paid": sales_count, "bookings": bookings_count, "turnover": turnover, "connection": connection,
        "next_action": _next_action(business, connection, click_count, conversations, sales_count, bookings_count),
        "connection_blockers": connection_blockers(connection), "affiliate": affiliate, "renewal_plan": plan,
        "renewal_url": f"{reverse('provider_special_offer')}?{urlencode({'business': business.pk, 'plan': plan.code})}" if plan else "",
    })


@login_required
@require_POST
@transaction.atomic
def update_partner_support(request, business_id):
    business = get_object_or_404(BusinessProfile.objects.select_for_update(), pk=business_id, owner=request.user)
    enabled = request.POST.get("support") == "yes"
    referral = Referral.objects.filter(referred_user=request.user, affiliate__is_enabled=True, affiliate__user__is_active=True).select_related("affiliate").first()
    if enabled and not referral:
        messages.error(request, "Aucun partenaire actif n’est associé à ton compte.")
    elif enabled != business.partner_support_enabled:
        business.partner_support_enabled = enabled
        business.save(update_fields=["partner_support_enabled"])
        if enabled:
            Notification.objects.create(
                destinataire_id=referral.affiliate.user_id, type_notif="systeme", titre="Un prestataire partage son suivi",
                message=f"{business.name} te donne accès à ses étapes d’accompagnement dans ton portefeuille.",
                url_action=reverse("business:partner_portfolio"),
            )
        messages.success(request, "Suivi partagé avec ton partenaire." if enabled else "Partage du suivi désactivé.")
    return redirect("business:business_progress", business_id=business.pk)


@login_required
@require_GET
@never_cache
def partner_portfolio(request):
    profile = AffiliateProfile.objects.filter(user=request.user, is_enabled=True, user__is_active=True).first()
    referrals = Referral.objects.filter(affiliate=profile) if profile else Referral.objects.none()
    rows = BusinessProfile.objects.filter(
        owner_id__in=referrals.values("referred_user_id"), partner_support_enabled=True,
    ).annotate(
        agent_running=Exists(BusinessWhatsAppConnection.objects.filter(
            business_id=OuterRef("pk"), agent_enabled=True, status=BusinessWhatsAppConnection.Status.ACTIVE,
            activation__activated_at__isnull=False,
        )), has_sale=Exists(_paid(OuterRef("pk"))), has_booking=Exists(_appointments(OuterRef("pk"))),
    ).order_by("subscription_expires_at", "name", "pk")
    page = Paginator(rows, 25).get_page(request.GET.get("page"))
    now = timezone.now()
    for business in page:
        if business.subscription_expires_at and not business.subscription_active:
            business.support_status = "Abonnement arrivé à échéance"
        elif business.subscription_expires_at and business.subscription_expires_at <= now + timedelta(days=7):
            business.support_status = "Renouvellement à préparer"
        elif not business.subscription_active:
            business.support_status = "Première formule à choisir"
        elif business.plan not in {BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM}:
            business.support_status = "Fiche à accompagner"
        elif not business.agent_running:
            business.support_status = "Mise en route à accompagner"
        elif not (business.has_sale or business.has_booking):
            business.support_status = "Premier résultat à accompagner"
        else:
            business.support_status = "Premier résultat atteint"
    ledger = Commission.objects.filter(
        affiliate=profile, transaction__status="COMPLETED", transaction__metadata__product_type="provider_subscription",
        status__in=["PENDING", "PAID"],
    ) if profile else Commission.objects.none()
    sums = ledger.filter(created_at__gte=now - timedelta(days=30)).order_by().values("currency", "status").annotate(total=Sum("amount"))
    renewals = ledger.filter(transaction__metadata__provider_payment_cycle="renewal", created_at__gte=now - timedelta(days=30)).count()
    invite = request.build_absolute_uri(reverse("public_ref_redirect", args=[profile.ref_code]) + "?" + urlencode({"next": reverse("business:onboarding")})) if profile else ""
    return render(request, "business/partner_portfolio.html", {"page": page, "sums": sums, "renewals": renewals, "invite": invite})


@login_required
@require_GET
@never_cache
def partner_sales(request):
    profile = AffiliateProfile.objects.filter(user=request.user).first()
    history = Commission.objects.filter(affiliate=profile) if profile else Commission.objects.none()
    status = request.GET.get("statut", "")
    if status in dict(Commission.STATUS_CHOICES):
        history = history.filter(status=status)
    else:
        status = ""
    product = request.GET.get("offre", "")
    if product in {"provider_subscription", "business_key_subscription"}:
        history = history.filter(transaction__metadata__product_type=product)
    else:
        product = ""
    page = Paginator(history.select_related("transaction__user").order_by("-created_at", "-pk"), 30).get_page(request.GET.get("page"))
    business_ids = set()
    for commission in page:
        identifier = (commission.transaction.metadata or {}).get("business_id")
        if isinstance(identifier, int) and not isinstance(identifier, bool):
            business_ids.add(identifier)
    shared = {(business.pk, business.owner_id): business.display_name for business in BusinessProfile.objects.filter(
        pk__in=business_ids, partner_support_enabled=True, owner__referral__affiliate=profile,
    )} if profile and profile.is_enabled else {}
    for commission in page:
        tx = commission.transaction
        meta = tx.metadata or {}
        kind = meta.get("product_type")
        commission.sale_kind = {"provider_subscription": "Abonnement prestataire", "business_key_subscription": "Business Key"}.get(kind, "Abonnement E‑Shelle")
        commission.sale_cycle = {"activation": "Activation", "renewal": "Renouvellement"}.get(meta.get("provider_payment_cycle"), "")
        commission.sale_plan = (meta.get("provider_plan_name") or meta.get("provider_plan", "")) if kind == "provider_subscription" else ""
        identifier = meta.get("business_id") if kind == "provider_subscription" else None
        if isinstance(identifier, int) and not isinstance(identifier, bool):
            commission.fiche = shared.get((identifier, tx.user_id)) or f"Fiche #{identifier}"
        else:
            commission.fiche = ""
        commission.percent = commission.rate * 100
    return render(request, "business/partner_sales.html", {"page": page, "status": status, "product": product})
