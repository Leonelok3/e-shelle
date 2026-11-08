import re
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Booking,
    LiveBooking,
    LivePackage,
    LiveSession,
    LiveSlot,
    OCDPackage,
    Opportunity,
    OpportunityCategory,
    Slot,
)
from .services.booking_service import create_booking_for_session, create_booking_for_slot, confirm_booking_payment
from .services.payment_bridge import initiate_booking_payment
from .services.pdf_service import generate_live_booking_pdf


def _clean_cameroon_phone(phone: str) -> tuple[str, bool]:
    """Valide et formate un numéro WhatsApp (priorité Cameroun +237)."""
    raw = phone.strip()
    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return "", False
    # Format Cameroun : 9 chiffres commençant par 6 (MTN / Orange / Nexttel / Camtel)
    if len(digits) == 9 and digits.startswith("6"):
        return f"+237{digits}", True
    # Format Cameroun avec indicatif 237 : 12 chiffres
    if len(digits) == 12 and digits.startswith("237"):
        return f"+{digits}", True
    # Format international standard >= 8 chiffres
    if len(digits) >= 8:
        if raw.startswith("+"):
            return f"+{digits}", True
        return f"+{digits}", True
    return raw, False


def index(request):
    """Vitrine principale OCD LIVE : Réservez votre passage en direct pour présenter vos produits et services devant l'audience E-Shelle."""
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
    
    # Packages officiels de passage en direct Live OCD
    live_packages = LivePackage.objects.filter(actif=True).order_by("ordre", "prix_xaf")
    # Legacy packages
    packages = OCDPackage.objects.filter(is_active=True).order_by("order", "price_xaf")
    categories = OpportunityCategory.objects.all()

    return render(
        request,
        "ocd_live/index.html",
        {
            "next_live": next_live,
            "featured_opportunities": featured_opportunities,
            "upcoming_lives": upcoming_lives,
            "live_packages": live_packages,
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
    my_live_bookings = LiveBooking.objects.filter(email=request.user.email).select_related("package", "slot").order_by("-date_creation")
    
    return render(
        request,
        "ocd_live/dashboard.html",
        {
            "bookings": bookings,
            "confirmed_bookings": confirmed_bookings,
            "my_live_bookings": my_live_bookings,
        },
    )


# ============================================================================
# SYSTÈME DE RÉSERVATION LIVE PITCH & VENTE OCD LIVE
# ============================================================================

def live_reservation(request):
    """
    Formulaire public de réservation OCD Live (4 étapes en 1 page mobile-first) :
    1. Ton activité & contacts
    2. Ton créneau (calendrier des slots disponibles >= demain)
    3. Ton package / Ta durée
    4. Paiement pour confirmer + upload preuve
    """
    tomorrow = timezone.localdate() + timedelta(days=1)
    packages = LivePackage.objects.filter(actif=True).order_by("ordre", "prix_xaf")

    booked_slot_ids = LiveBooking.objects.filter(
        statut__in=[
            LiveBooking.Statut.VALIDEE_ADMIN,
            LiveBooking.Statut.CONFIRMEE,
            LiveBooking.Statut.EN_ATTENTE_VALIDATION,
        ],
        slot__isnull=False,
    ).values_list("slot_id", flat=True)

    available_slots = (
        LiveSlot.objects.filter(
            date__gte=tomorrow,
            est_disponible=True,
            est_bloque_admin=False,
        )
        .exclude(pk__in=booked_slot_ids)
        .order_by("date", "heure_debut")
    )

    selected_package_id = request.GET.get("package", "")
    selected_slot_id = request.GET.get("slot", "")

    errors = {}
    form_data = {}

    if request.user.is_authenticated:
        form_data["nom_complet"] = request.user.get_full_name() or request.user.username
        form_data["email"] = request.user.email

    if request.method == "POST":
        form_data = {
            "nom_complet": request.POST.get("nom_complet", "").strip(),
            "telephone_whatsapp": request.POST.get("telephone_whatsapp", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "nom_entreprise": request.POST.get("nom_entreprise", "").strip(),
            "secteur_activite": request.POST.get("secteur_activite", "").strip(),
            "titre_du_live": request.POST.get("titre_du_live", "").strip(),
            "description_activite": request.POST.get("description_activite", "").strip(),
            "produits_services": request.POST.get("produits_services", "").strip(),
            "lien_site_ou_page": request.POST.get("lien_site_ou_page", "").strip(),
            "lien_whatsapp": request.POST.get("lien_whatsapp", "").strip(),
            "package_id": request.POST.get("package_id", "").strip(),
            "slot_id": request.POST.get("slot_id", "").strip(),
            "mode_paiement": request.POST.get("mode_paiement", "").strip(),
            "reference_paiement": request.POST.get("reference_paiement", "").strip(),
        }

        # Validation des champs obligatoires
        required_fields = [
            ("nom_complet", "Le nom complet est obligatoire."),
            ("telephone_whatsapp", "Le numéro WhatsApp est obligatoire."),
            ("email", "L'adresse email est obligatoire."),
            ("nom_entreprise", "Le nom de l'entreprise ou marque est obligatoire."),
            ("secteur_activite", "Veuillez choisir votre secteur d'activité."),
            ("titre_du_live", "Le titre de votre passage Live est obligatoire."),
            ("description_activite", "La description de votre présentation est obligatoire."),
            ("produits_services", "La liste des produits/services présentés est obligatoire."),
            ("package_id", "Veuillez choisir votre formule / package."),
            ("slot_id", "Veuillez sélectionner un créneau horaire disponible."),
            ("mode_paiement", "Veuillez sélectionner votre mode de règlement."),
        ]

        for field, err_msg in required_fields:
            if not form_data.get(field):
                errors[field] = err_msg

        cleaned_phone, is_phone_valid = _clean_cameroon_phone(form_data.get("telephone_whatsapp", ""))
        if form_data.get("telephone_whatsapp") and not is_phone_valid:
            errors["telephone_whatsapp"] = "Numéro WhatsApp invalide (ex: 680625082 ou +237680625082)."
        else:
            form_data["telephone_whatsapp"] = cleaned_phone

        package = None
        if form_data.get("package_id"):
            package = LivePackage.objects.filter(pk=form_data["package_id"], actif=True).first()
            if not package:
                errors["package_id"] = "Le package sélectionné est invalide ou inactif."

        slot = None
        if form_data.get("slot_id"):
            try:
                slot_id_val = int(form_data["slot_id"])
                slot = LiveSlot.objects.filter(pk=slot_id_val).first()
                if not slot:
                    errors["slot_id"] = "Le créneau sélectionné n'existe pas."
                elif slot.date < tomorrow:
                    errors["slot_id"] = "La date du direct doit être fixée au plus tôt pour demain."
                elif not slot.est_reservable:
                    errors["slot_id"] = "Ce créneau horaire n'est plus disponible. Veuillez en sélectionner un autre."
            except (ValueError, TypeError):
                errors["slot_id"] = "Créneau invalide."

        if not errors and package and slot:
            try:
                with transaction.atomic():
                    locked_slot = LiveSlot.objects.select_for_update().get(pk=slot.pk)
                    if not locked_slot.est_reservable:
                        errors["slot_id"] = "Ce créneau vient d'être réservé par un autre utilisateur. Veuillez en choisir un autre."
                        raise ValueError("Conflit de créneau")

                    preuve_file = request.FILES.get("preuve_paiement")
                    statut_initial = LiveBooking.Statut.EN_ATTENTE_PAIEMENT
                    if preuve_file or form_data["reference_paiement"]:
                        statut_initial = LiveBooking.Statut.EN_ATTENTE_VALIDATION

                    booking = LiveBooking.objects.create(
                        nom_complet=form_data["nom_complet"],
                        telephone_whatsapp=form_data["telephone_whatsapp"],
                        email=form_data["email"],
                        nom_entreprise=form_data["nom_entreprise"],
                        secteur_activite=form_data["secteur_activite"],
                        titre_du_live=form_data["titre_du_live"],
                        description_activite=form_data["description_activite"],
                        produits_services=form_data["produits_services"],
                        lien_site_ou_page=form_data["lien_site_ou_page"],
                        lien_whatsapp=form_data["lien_whatsapp"],
                        package=package,
                        slot=locked_slot,
                        date_choisie=locked_slot.date,
                        heure_choisie=locked_slot.heure_debut,
                        duree_minutes=package.duree_minutes,
                        prix_total=package.prix_xaf,
                        mode_paiement=form_data["mode_paiement"],
                        reference_paiement=form_data["reference_paiement"],
                        preuve_paiement=preuve_file,
                        statut=statut_initial,
                    )

                    messages.success(
                        request,
                        f"🎉 Votre réservation de passage en direct a été enregistrée avec succès ! Code : {booking.code_reservation}",
                    )
                    return redirect("ocd_live:suivi", code=booking.code_reservation)

            except ValueError:
                pass
            except Exception as e:
                errors["global"] = f"Une erreur inattendue est survenue lors de l'enregistrement : {str(e)}"

    return render(
        request,
        "ocd_live/reservation_form.html",
        {
            "packages": packages,
            "available_slots": available_slots,
            "secteurs": LiveBooking.SecteurActivite.choices,
            "modes_paiement": LiveBooking.ModePaiement.choices,
            "selected_package_id": selected_package_id,
            "selected_slot_id": selected_slot_id,
            "form_data": form_data,
            "errors": errors,
        },
    )


def live_suivi(request, code):
    """
    Page de suivi public de la réservation OCD Live :
    Affiche le statut en temps réel, le récapitulatif, la preuve de paiement,
    et le bouton pour télécharger la fiche PDF officielle.
    """
    clean_code = code.strip().upper()
    booking = get_object_or_404(
        LiveBooking.objects.select_related("package", "slot"),
        code_reservation=clean_code,
    )

    if request.method == "POST":
        reference_paiement = request.POST.get("reference_paiement", "").strip()
        mode_paiement = request.POST.get("mode_paiement", "").strip()
        preuve_file = request.FILES.get("preuve_paiement")

        updated = False
        if reference_paiement:
            booking.reference_paiement = reference_paiement
            updated = True
        if mode_paiement:
            booking.mode_paiement = mode_paiement
            updated = True
        if preuve_file:
            booking.preuve_paiement = preuve_file
            updated = True

        if updated:
            if booking.statut == LiveBooking.Statut.EN_ATTENTE_PAIEMENT:
                booking.statut = LiveBooking.Statut.EN_ATTENTE_VALIDATION
            booking.save()
            messages.success(
                request,
                "✓ Vos informations de paiement ont été transmises. Notre régie vérifie votre dossier sous 24h.",
            )
            return redirect("ocd_live:suivi", code=booking.code_reservation)

    return render(
        request,
        "ocd_live/suivi.html",
        {
            "booking": booking,
            "modes_paiement": LiveBooking.ModePaiement.choices,
        },
    )


def live_fiche_pdf(request, code):
    """Génère et télécharge la fiche officielle de réservation au format PDF."""
    clean_code = code.strip().upper()
    booking = get_object_or_404(
        LiveBooking.objects.select_related("package", "slot"),
        code_reservation=clean_code,
    )
    pdf_bytes = generate_live_booking_pdf(booking)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="Fiche_Reservation_OCD_Live_{booking.code_reservation}.pdf"'
    return response


@staff_member_required
def live_admin_dashboard(request):
    """Tableau de bord administrateur OCD Live (protégé login staff)."""
    total_demandes = LiveBooking.objects.count()
    en_attente_count = LiveBooking.objects.filter(
        statut__in=[
            LiveBooking.Statut.EN_ATTENTE,
            LiveBooking.Statut.EN_ATTENTE_PAIEMENT,
            LiveBooking.Statut.EN_ATTENTE_VALIDATION,
        ]
    ).count()
    validees_count = LiveBooking.objects.filter(
        statut__in=[LiveBooking.Statut.VALIDEE_ADMIN, LiveBooking.Statut.CONFIRMEE]
    ).count()
    revenu_confirme = (
        LiveBooking.objects.filter(
            statut__in=[LiveBooking.Statut.VALIDEE_ADMIN, LiveBooking.Statut.CONFIRMEE]
        ).aggregate(total=Sum("prix_total"))["total"]
        or Decimal("0.00")
    )

    bookings = LiveBooking.objects.select_related("package", "slot").order_by("-date_creation")

    statut_filter = request.GET.get("statut", "").strip()
    if statut_filter:
        bookings = bookings.filter(statut=statut_filter)

    date_filter = request.GET.get("date", "").strip()
    if date_filter:
        try:
            d_val = datetime.strptime(date_filter, "%Y-%m-%d").date()
            bookings = bookings.filter(date_choisie=d_val)
        except ValueError:
            pass

    q = request.GET.get("q", "").strip()
    if q:
        bookings = bookings.filter(
            Q(code_reservation__icontains=q)
            | Q(nom_complet__icontains=q)
            | Q(nom_entreprise__icontains=q)
            | Q(telephone_whatsapp__icontains=q)
            | Q(email__icontains=q)
        )

    if request.method == "POST" and "create_slot" in request.POST:
        slot_date = request.POST.get("slot_date")
        h_deb = request.POST.get("heure_debut")
        h_fin = request.POST.get("heure_fin")
        if slot_date and h_deb and h_fin:
            try:
                d_obj = datetime.strptime(slot_date, "%Y-%m-%d").date()
                h_deb_obj = datetime.strptime(h_deb, "%H:%M").time()
                h_fin_obj = datetime.strptime(h_fin, "%H:%M").time()
                LiveSlot.objects.create(
                    date=d_obj,
                    heure_debut=h_deb_obj,
                    heure_fin=h_fin_obj,
                    capacite=1,
                    est_disponible=True,
                )
                messages.success(request, f"Créneau du {d_obj.strftime('%d/%m/%Y')} de {h_deb} à {h_fin} créé avec succès.")
                return redirect("ocd_live:admin_dashboard")
            except Exception as e:
                messages.error(request, f"Erreur lors de la création du créneau : {e}")

    paginator = Paginator(bookings, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "ocd_live/admin_dashboard.html",
        {
            "total_demandes": total_demandes,
            "en_attente_count": en_attente_count,
            "validees_count": validees_count,
            "revenu_confirme": revenu_confirme,
            "page_obj": page_obj,
            "statut_filter": statut_filter,
            "date_filter": date_filter,
            "q": q,
            "statut_choices": LiveBooking.Statut.choices,
        },
    )


@staff_member_required
def live_admin_action(request, booking_id):
    """Actions administrateur : valider, refuser, annuler, marquer terminée."""
    if request.method != "POST":
        return redirect("ocd_live:admin_dashboard")

    booking = get_object_or_404(LiveBooking.objects.select_related("slot"), pk=booking_id)
    action = request.POST.get("action", "").strip()
    message_admin = request.POST.get("message_admin", "").strip()

    if message_admin:
        booking.message_admin = message_admin

    if action == "valider":
        booking.statut = LiveBooking.Statut.VALIDEE_ADMIN
        if booking.slot:
            booking.slot.est_disponible = False
            booking.slot.save(update_fields=["est_disponible"])
        booking.save()
        messages.success(
            request,
            f"✓ Réservation {booking.code_reservation} validée avec succès ! Le créneau a été verrouillé.",
        )
    elif action == "refuser":
        booking.statut = LiveBooking.Statut.REFUSEE
        if booking.slot:
            has_other = booking.slot.bookings.exclude(pk=booking.pk).filter(
                statut__in=[LiveBooking.Statut.VALIDEE_ADMIN, LiveBooking.Statut.CONFIRMEE]
            ).exists()
            if not has_other:
                booking.slot.est_disponible = True
                booking.slot.save(update_fields=["est_disponible"])
        booking.save()
        messages.warning(request, f"La réservation {booking.code_reservation} a été refusée.")
    elif action == "annuler":
        booking.statut = LiveBooking.Statut.ANNULEE
        if booking.slot:
            has_other = booking.slot.bookings.exclude(pk=booking.pk).filter(
                statut__in=[LiveBooking.Statut.VALIDEE_ADMIN, LiveBooking.Statut.CONFIRMEE]
            ).exists()
            if not has_other:
                booking.slot.est_disponible = True
                booking.slot.save(update_fields=["est_disponible"])
        booking.save()
        messages.info(request, f"La réservation {booking.code_reservation} a été annulée.")
    elif action == "terminee":
        booking.statut = LiveBooking.Statut.TERMINEE
        booking.save()
        messages.success(request, f"La session {booking.code_reservation} est désormais marquée comme terminée.")

    return redirect("ocd_live:admin_dashboard")


def live_available_slots_api(request):
    """API JSON retournant les créneaux disponibles pour une date donnée."""
    date_str = request.GET.get("date", "").strip()
    if not date_str:
        return JsonResponse({"slots": []})

    try:
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Format de date invalide (YYYY-MM-DD)"}, status=400)

    booked_slot_ids = LiveBooking.objects.filter(
        statut__in=[
            LiveBooking.Statut.VALIDEE_ADMIN,
            LiveBooking.Statut.CONFIRMEE,
            LiveBooking.Statut.EN_ATTENTE_VALIDATION,
        ],
        slot__isnull=False,
    ).values_list("slot_id", flat=True)

    slots = LiveSlot.objects.filter(
        date=query_date,
        est_disponible=True,
        est_bloque_admin=False,
    ).exclude(pk__in=booked_slot_ids).order_by("heure_debut")

    data = [
        {
            "id": s.id,
            "date": s.date.isoformat(),
            "heure_debut": s.heure_debut.strftime("%H:%M"),
            "heure_fin": s.heure_fin.strftime("%H:%M"),
            "label": f"{s.heure_debut.strftime('%H:%M')} - {s.heure_fin.strftime('%H:%M')}",
        }
        for s in slots
    ]
    return JsonResponse({"date": date_str, "slots": data})


