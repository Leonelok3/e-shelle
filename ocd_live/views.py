from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Booking, LiveSession, OCDPackage, Opportunity, OpportunityCategory, Slot
from .services.booking_service import create_booking_for_session, create_booking_for_slot, confirm_booking_payment
from .services.payment_bridge import initiate_booking_payment


def index(request):
    """Vitrine principale OCD LIVE — Les Opportunités C'est Dehors."""
    now = timezone.now()
    next_live = (
        LiveSession.objects.filter(is_live_now=True).first()
        or LiveSession.objects.filter(scheduled_at__gte=now, is_completed=False).order_by("scheduled_at").first()
    )
    featured_opportunities = Opportunity.objects.filter(
        status__in=[Opportunity.Status.VERIFIED, Opportunity.Status.IN_PROGRESS]
    ).select_related("category")[:6]
    
    upcoming_lives = LiveSession.objects.filter(is_completed=False).exclude(
        pk=next_live.pk if next_live else 0
    ).order_by("scheduled_at")[:4]
    
    packages = OCDPackage.objects.filter(is_active=True).order_by("order", "price_xaf")
    categories = OpportunityCategory.objects.all()

    return render(
        request,
        "ocd_live/index.html",
        {
            "next_live": next_live,
            "featured_opportunities": featured_opportunities,
            "upcoming_lives": upcoming_lives,
            "packages": packages,
            "categories": categories,
        },
    )


def opportunities_list(request):
    """Catalogue public des opportunités d'affaires vérifiées en Afrique."""
    opportunities = Opportunity.objects.all().select_related("category")
    
    cat_slug = request.GET.get("category", "").strip()
    if cat_slug:
        opportunities = opportunities.filter(category__slug=cat_slug)
        
    query = request.GET.get("q", "").strip()
    if query:
        opportunities = opportunities.filter(
            Q(title__icontains=query) | Q(summary__icontains=query) | Q(city__icontains=query)
        )

    paginator = Paginator(opportunities, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    categories = OpportunityCategory.objects.all()

    return render(
        request,
        "ocd_live/opportunities_list.html",
        {
            "page_obj": page_obj,
            "categories": categories,
            "active_category": cat_slug,
            "query": query,
        },
    )


def opportunity_detail(request, slug):
    """Fiche détaillée d'une opportunité avec contact WhatsApp terrain."""
    opportunity = get_object_or_404(Opportunity.objects.select_related("category"), slug=slug)
    Opportunity.objects.filter(pk=opportunity.pk).update(views_count=opportunity.views_count + 1)
    
    related = Opportunity.objects.filter(
        category=opportunity.category
    ).exclude(pk=opportunity.pk)[:3]

    return render(
        request,
        "ocd_live/opportunity_detail.html",
        {
            "opportunity": opportunity,
            "related": related,
        },
    )


def live_list(request):
    """Programme complet des sessions Live & Replays."""
    now = timezone.now()
    active_lives = LiveSession.objects.filter(is_live_now=True)
    upcoming_lives = LiveSession.objects.filter(is_live_now=False, is_completed=False, scheduled_at__gte=now)
    past_replays = LiveSession.objects.filter(is_completed=True).order_by("-scheduled_at")[:6]

    return render(
        request,
        "ocd_live/live_list.html",
        {
            "active_lives": active_lives,
            "upcoming_lives": upcoming_lives,
            "past_replays": past_replays,
        },
    )


def live_detail(request, slug):
    """Salle de session Live / Masterclass avec lecteur de diffusion et interactivité."""
    session = get_object_or_404(LiveSession, slug=slug)
    
    # Vérification si l'utilisateur a un ticket confirmé
    has_access = False
    if session.access_tier == LiveSession.AccessTier.FREE:
        has_access = True
    elif request.user.is_authenticated:
        if request.user.is_superuser:
            has_access = True
        else:
            has_access = Booking.objects.filter(
                user=request.user,
                session=session,
                status=Booking.Status.CONFIRMED,
            ).exists()

    available_slots = session.slots.filter(is_active=True).order_by("start_time")

    return render(
        request,
        "ocd_live/live_detail.html",
        {
            "session": session,
            "has_access": has_access,
            "available_slots": available_slots,
        },
    )


@login_required
def book_session(request, slug):
    """Réservation d'une place pour une session Live ou un créneau privé."""
    session = get_object_or_404(LiveSession, slug=slug)
    
    if request.method == "POST":
        whatsapp = request.POST.get("whatsapp", "").strip()
        booking = create_booking_for_session(request.user, session, whatsapp_number=whatsapp)
        
        if booking.status == Booking.Status.CONFIRMED:
            messages.success(request, "Votre inscription gratuite est confirmée !")
            return redirect("ocd_live:booking_detail", ticket_code=booking.ticket_code)
        
        # Redirection vers paiement CamPay Mobile Money
        payment_redirect = initiate_booking_payment(request, booking)
        if payment_redirect:
            return payment_redirect

        return redirect("ocd_live:booking_detail", ticket_code=booking.ticket_code)

    return render(request, "ocd_live/booking_form.html", {"session": session})


@login_required
def book_package(request, package_code):
    """Souscription à un Pass OCD Live (Découverte, Mensuel, VIP)."""
    package = get_object_or_404(OCDPackage, code=package_code, is_active=True)

    if request.method == "POST":
        whatsapp = request.POST.get("whatsapp", "").strip()
        booking = Booking.objects.create(
            user=request.user,
            package=package,
            amount_paid=package.price_xaf,
            status=Booking.Status.PENDING,
            whatsapp_number=whatsapp,
        )
        payment_redirect = initiate_booking_payment(request, booking)
        if payment_redirect:
            return payment_redirect

        return redirect("ocd_live:booking_detail", ticket_code=booking.ticket_code)

    return render(request, "ocd_live/package_checkout.html", {"package": package})


def booking_detail(request, ticket_code):
    """Affichage du billet / reçu avec code d'accès unique."""
    booking = get_object_or_404(Booking.objects.select_related("user", "session", "package", "slot"), ticket_code=ticket_code)
    
    return render(
        request,
        "ocd_live/booking_detail.html",
        {
            "booking": booking,
        },
    )


@login_required
def dashboard(request):
    """Espace Membre OCD LIVE : mes billets, mes créneaux et mes replays."""
    bookings = Booking.objects.filter(user=request.user).select_related("session", "package", "slot")
    confirmed_bookings = bookings.filter(status=Booking.Status.CONFIRMED)
    
    return render(
        request,
        "ocd_live/dashboard.html",
        {
            "bookings": bookings,
            "confirmed_bookings": confirmed_bookings,
        },
    )

