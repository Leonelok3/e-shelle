from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Case, When, Value, IntegerField
from django.contrib import messages
from django.urls import reverse

from .models import AusbildungOffer, ScholarshipOpportunity, UserOpportunityBookmark


def check_user_has_germany_premium(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        from accounts.models import AppSubscription
        sub = AppSubscription.get_active_for_user(user, "allemand")
        if sub and sub.is_active and not sub.plan.is_free:
            return True
    except Exception:
        pass
    return False


SECTOR_LABELS = {
    "gesundheit":  ("Sante & Soins",      "heart-pulse"),
    "it":          ("IT & Informatique",   "laptop-code"),
    "elektro":     ("Electrotechnique",    "bolt"),
    "bau":         ("BTP & Artisanat",     "hard-hat"),
    "hotellerie":  ("Hotellerie & Resto",  "utensils"),
    "logistik":    ("Logistique",          "truck"),
    "kaufmann":    ("Commerce & Bureau",   "briefcase"),
    "soziales":    ("Social & Education",  "child"),
    "andere":      ("Autre",               "star"),
}


def catalogue(request):
    """Page principale des opportunites : filtres + grille d'offres."""
    has_premium = check_user_has_germany_premium(request.user)
    sector    = request.GET.get("sector", "")
    level     = request.GET.get("level", "")
    city_q    = request.GET.get("city", "")
    region_q  = request.GET.get("region", "")
    search_q  = request.GET.get("q", "")
    sort      = request.GET.get("sort", "newest")

    from datetime import date as dt_date
    offers = AusbildungOffer.objects.filter(is_active=True).filter(
        Q(start_date__isnull=True) | Q(start_date__gte=dt_date.today())
    )

    if sector:
        offers = offers.filter(sector=sector)
    if level:
        offers = offers.filter(language_req=level)
    if city_q:
        offers = offers.filter(city__icontains=city_q)
    if region_q:
        offers = offers.filter(region__icontains=region_q)
    if search_q:
        offers = offers.filter(
            Q(title__icontains=search_q) |
            Q(company__icontains=search_q) |
            Q(description__icontains=search_q)
        )

    if sort == "soonest":
        offers = offers.order_by(
            Case(
                When(start_date__isnull=False, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            "start_date",
            "-fetched_at",
            "-pk",
        )
    elif sort == "alphabetical":
        offers = offers.order_by("title", "-fetched_at", "-pk")
    else:
        offers = offers.order_by("-fetched_at", "-pk")

    # Bookmarks de l'utilisateur connecte
    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(
            UserOpportunityBookmark.objects.filter(
                user=request.user, offer__isnull=False
            ).values_list("offer_id", flat=True)
        )

    # Pagination : 24 offres par page
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(offers, 24)
    page = request.GET.get("page")
    try:
        paginated_offers = paginator.page(page)
    except PageNotAnInteger:
        paginated_offers = paginator.page(1)
    except EmptyPage:
        paginated_offers = paginator.page(paginator.num_pages)

    scholarships = ScholarshipOpportunity.objects.filter(is_active=True).order_by("deadline")[:6]
    has_active_filters = any([sector, level, city_q, region_q, search_q])

    context = {
        "offers":         paginated_offers,
        "scholarships":   scholarships,
        "sector_labels":  SECTOR_LABELS,
        "active_sector":  sector,
        "active_level":   level,
        "active_region":  region_q,
        "active_sort":    sort,
        "city_q":         city_q,
        "search_q":       search_q,
        "bookmarked_ids": bookmarked_ids,
        "total_offers":   offers.count(),
        "sector_choices": AusbildungOffer.SECTOR_CHOICES,
        "level_choices":  AusbildungOffer.LANGUAGE_CHOICES,
        "has_active_filters": has_active_filters,
        "has_premium": has_premium,
    }
    return render(request, "germany_opportunities/catalogue.html", context)


def offer_detail(request, pk):
    """Detail d'une offre Ausbildung."""
    if not check_user_has_germany_premium(request.user):
        messages.warning(request, "L'accès aux détails des offres d'Ausbildung est réservé aux membres Premium.")
        return redirect("germany_opportunities:premium_pricing")

    offer = get_object_or_404(AusbildungOffer, pk=pk, is_active=True)
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = UserOpportunityBookmark.objects.filter(
            user=request.user, offer=offer
        ).exists()

    similar = AusbildungOffer.objects.filter(
        sector=offer.sector, is_active=True
    ).exclude(pk=offer.pk).order_by("-fetched_at", "-pk")[:4]

    context = {
        "offer":        offer,
        "is_bookmarked": is_bookmarked,
        "similar":      similar,
    }
    return render(request, "germany_opportunities/offer_detail.html", context)


@login_required
@require_POST
def toggle_bookmark(request, pk):
    """Toggle bookmark AJAX (JSON response)."""
    offer = get_object_or_404(AusbildungOffer, pk=pk)
    bm, created = UserOpportunityBookmark.objects.get_or_create(
        user=request.user, offer=offer
    )
    if not created:
        bm.delete()
        bookmark_count = UserOpportunityBookmark.objects.filter(
            user=request.user, offer__isnull=False
        ).count()
        return JsonResponse({"status": "removed", "bookmarked": False, "bookmark_count": bookmark_count})

    bookmark_count = UserOpportunityBookmark.objects.filter(
        user=request.user, offer__isnull=False
    ).count()
    return JsonResponse({"status": "saved", "bookmarked": True, "bookmark_count": bookmark_count})


@login_required
def my_bookmarks(request):
    """Liste des offres sauvegardees par l'utilisateur."""
    bookmarks = UserOpportunityBookmark.objects.filter(
        user=request.user
    ).select_related("offer", "scholarship")
    return render(request, "germany_opportunities/my_bookmarks.html", {"bookmarks": bookmarks})


@require_POST
@login_required
def mark_applied(request, pk):
    """Marquer une offre comme postule."""
    from django.utils import timezone
    bm = get_object_or_404(UserOpportunityBookmark, pk=pk, user=request.user)
    bm.applied = not bm.applied
    bm.applied_at = timezone.now() if bm.applied else None
    bm.save(update_fields=["applied", "applied_at"])
    return JsonResponse({"applied": bm.applied})


def candidate_profiles(request):
    """Affiche la liste publique des profils candidats ayant un abonnement premium (edu)."""
    from django.db.models import Q
    from django.utils import timezone
    from accounts.models import AppSubscription, CustomUser
    from lebenslauf.models import GermanCVProfile

    search_q = request.GET.get("q", "").strip()
    sector   = request.GET.get("sector", "").strip()
    level    = request.GET.get("level", "").strip()
    goethe   = request.GET.get("goethe", "").strip()

    # 1. Filtre les abonnements payants/actifs à 'edu'
    active_subs = AppSubscription.objects.filter(
        plan__app_key="edu",
        status__in=["active", "trial"]
    ).exclude(plan__is_free=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )
    subscribed_user_ids = active_subs.values_list("user_id", flat=True)

    # 2. Utilisateurs avec abonnements actifs ou plans pro/enterprise généraux, ou staff/superuser
    valid_users = CustomUser.objects.filter(
        Q(id__in=subscribed_user_ids) |
        Q(profile__plan__in=["pro", "enterprise"]) |
        Q(is_superuser=True) |
        Q(is_staff=True)
    )

    # 3. Profils de CV Allemand
    profiles = GermanCVProfile.objects.filter(user__in=valid_users).select_related(
        "user", "user__profile"
    ).prefetch_related(
        "user__cv_experiences", "user__cv_educations", "user__cv_languages"
    ).order_by("-updated_at")

    # Filtre recherche libre
    if search_q:
        profiles = profiles.filter(
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q) |
            Q(target_sector__icontains=search_q) |
            Q(target_cities__icontains=search_q) |
            Q(user__cv_experiences__title__icontains=search_q) |
            Q(user__cv_experiences__company__icontains=search_q) |
            Q(user__cv_educations__degree__icontains=search_q)
        ).distinct()

    # Filtre par secteur
    if sector:
        profiles = profiles.filter(target_sector__icontains=sector)

    # Filtre par niveau
    if level:
        profiles = profiles.filter(german_level=level)

    # Filtre certifié Goethe
    if goethe == "yes":
        profiles = profiles.filter(goethe_certified=True)

    context = {
        "profiles":       profiles,
        "search_q":       search_q,
        "active_sector":  sector,
        "active_level":   level,
        "active_goethe":  goethe,
        "sector_choices": AusbildungOffer.SECTOR_CHOICES,
        "level_choices":  GermanCVProfile.GERMAN_LEVEL_CHOICES,
    }
    return render(request, "germany_opportunities/candidate_profiles.html", context)


def top_companies(request):
    """Affiche la liste des 100 meilleures entreprises proposant des Ausbildung rémunérées."""
    from django.db.models import Count
    from .models import AusbildungOffer

    search_q = request.GET.get("q", "").strip()

    # Liste des 100 meilleures entreprises Ausbildung allemandes
    COMPANIES = [
        # Industrie & Ingénierie
        {"name": "Siemens AG", "sector": "Industrie & Ingénierie", "cities": "Munich, Berlin, Erlangen, Stuttgart"},
        {"name": "Bosch Group", "sector": "Industrie & Ingénierie", "cities": "Stuttgart, Gerlingen, Karlsruhe"},
        {"name": "Volkswagen AG", "sector": "Automobile & Industrie", "cities": "Wolfsburg, Hanovre, Kassel"},
        {"name": "Mercedes-Benz Group", "sector": "Automobile & Industrie", "cities": "Stuttgart, Brême, Sindelfingen"},
        {"name": "BMW Group", "sector": "Automobile & Industrie", "cities": "Munich, Ratisbonne, Leipzig"},
        {"name": "Porsche AG", "sector": "Automobile & Industrie", "cities": "Stuttgart, Leipzig"},
        {"name": "Continental AG", "sector": "Automobile & Industrie", "cities": "Hanovre, Francfort, Ratisbonne"},
        {"name": "Thyssenkrupp AG", "sector": "Industrie & Métallurgie", "cities": "Essen, Duisbourg, Dortmund"},
        {"name": "ZF Friedrichshafen AG", "sector": "Automobile & Industrie", "cities": "Friedrichshafen, Schweinfurt"},
        {"name": "BASF SE", "sector": "Chimie & Industrie", "cities": "Ludwigshafen, Schwarzheide"},
        {"name": "Bayer AG", "sector": "Pharmacie & Chimie", "cities": "Leverkusen, Berlin, Wuppertal"},
        {"name": "Merck KGaA", "sector": "Pharmacie & Chimie", "cities": "Darmstadt"},
        {"name": "Evonik Industries AG", "sector": "Chimie & Industrie", "cities": "Essen, Hanau, Marl"},
        {"name": "Covestro AG", "sector": "Chimie & Industrie", "cities": "Leverkusen, Dormagen"},
        {"name": "Linde plc", "sector": "Gaz & Ingénierie", "cities": "Munich, Pullach"},
        {"name": "Henkel AG & Co. KGaA", "sector": "Biens de consommation", "cities": "Düsseldorf"},
        {"name": "Heidelberg Materials", "sector": "Matériaux de construction", "cities": "Heidelberg"},
        {"name": "Beiersdorf AG", "sector": "Biens de consommation", "cities": "Hambourg"},
        {"name": "Miele & Cie. KG", "sector": "Électroménager & Industrie", "cities": "Gütersloh, Bielefeld"},
        {"name": "Liebherr-International", "sector": "Machines & Industrie", "cities": "Biberach, Ehingen"},
        {"name": "Kärcher (Alfred Kärcher SE & Co. KG)", "sector": "Nettoyage & Industrie", "cities": "Winnenden"},
        {"name": "Trumpf SE + Co. KG", "sector": "Machines-outils & Laser", "cities": "Ditzingen"},
        {"name": "Festo SE & Co. KG", "sector": "Automatisation & Industrie", "cities": "Esslingen"},
        {"name": "Phoenix Contact GmbH & Co. KG", "sector": "Électronique & Industrie", "cities": "Blomberg"},
        {"name": "Beckhoff Automation", "sector": "Automatisation & Industrie", "cities": "Verl"},
        {"name": "SEW-EURODRIVE GmbH & Co KG", "sector": "Moteurs & Automatisation", "cities": "Bruchsal"},
        {"name": "Sick AG", "sector": "Capteurs & Technologie", "cities": "Waldkirch"},
        {"name": "Endress+Hauser", "sector": "Technique de mesure", "cities": "Weil am Rhein"},
        {"name": "WAGO GmbH & Co. KG", "sector": "Connexions électriques", "cities": "Minden"},
        {"name": "Rittal GmbH & Co. KG", "sector": "Armoires électriques", "cities": "Herborn"},
        {"name": "Schaeffler AG", "sector": "Automobile & Industrie", "cities": "Herzogenaurach, Schweinfurt"},
        {"name": "Bosch Rexroth AG", "sector": "Hydraulique & Industrie", "cities": "Lohr am Main"},
        {"name": "Carl Zeiss AG", "sector": "Optique & Technologie", "cities": "Oberkochen, Iéna"},
        {"name": "Jenoptik AG", "sector": "Optique & Technologie", "cities": "Iéna"},
        {"name": "Leica Camera AG", "sector": "Optique & Photographie", "cities": "Wetzlar"},
        {"name": "Sennheiser electronic", "sector": "Audio & Technologie", "cities": "Wedemark"},
        {"name": "Hilti Deutschland", "sector": "Outillage & Construction", "cities": "Kaufering"},
        {"name": "Würth Gruppe", "sector": "Fixation & Outillage", "cities": "Künzelsau"},
        {"name": "STIHL AG", "sector": "Motoculture & Outillage", "cities": "Waiblingen"},
        {"name": "Krones AG", "sector": "Emballage & Machines", "cities": "Neutraubling"},
        {"name": "Salzgitter AG", "sector": "Acier & Métallurgie", "cities": "Salzgitter"},
        {"name": "SMS group GmbH", "sector": "Métallurgie & Machines", "cities": "Düsseldorf, Hilchenbach"},
        {"name": "Voith Group", "sector": "Ingénierie & Machines", "cities": "Heidenheim"},
        {"name": "Herrenknecht AG", "sector": "Tunneliers & Machines", "cities": "Schwanau"},
        {"name": "Viessmann Werke", "sector": "Chauffage & Énergie", "cities": "Allendorf"},
        {"name": "Wilo SE", "sector": "Pompes & Industrie", "cities": "Dortmund"},
        {"name": "HARTING Technology Group", "sector": "Connecteurs & Industrie", "cities": "Espelkamp"},
        {"name": "Weidmüller Interface", "sector": "Connexions électriques", "cities": "Detmold"},
        {"name": "Pepperl+Fuchs SE", "sector": "Capteurs & Automatisation", "cities": "Mannheim"},
        
        # IT & Technologie
        {"name": "SAP SE", "sector": "IT & Logiciels", "cities": "Walldorf, Munich, Berlin, Karlsruhe"},
        {"name": "Deutsche Telekom AG", "sector": "Télécommunications & IT", "cities": "Bonn, Darmstadt, Francfort"},
        {"name": "Infineon Technologies AG", "sector": "Semi-conducteurs & IT", "cities": "Neubiberg, Dresde, Ratisbonne"},
        {"name": "Allianz Technology", "sector": "IT & Services", "cities": "Munich, Francfort"},
        {"name": "Software AG", "sector": "IT & Logiciels", "cities": "Darmstadt"},
        {"name": "Bechtle AG", "sector": "IT & Services", "cities": "Neckarsulm, Hambourg, Cologne"},
        {"name": "Adesso SE", "sector": "IT & Conseil", "cities": "Dortmund, Munich, Berlin"},
        {"name": "United Internet AG (1&1, GMX)", "sector": "Télécommunications & IT", "cities": "Montabaur, Karlsruhe"},
        
        # Transport & Logistique
        {"name": "Deutsche Bahn AG", "sector": "Transport & Logistique", "cities": "Berlin, Francfort, Munich, Stuttgart"},
        {"name": "Lufthansa Group", "sector": "Aviation & Logistique", "cities": "Francfort, Munich, Hambourg"},
        {"name": "DHL Group", "sector": "Transport & Logistique", "cities": "Bonn, Francfort, Leipzig"},
        {"name": "Fraport AG", "sector": "Transport & Gestion aéroportuaire", "cities": "Francfort"},
        {"name": "Hapag-Lloyd AG", "sector": "Transport maritime", "cities": "Hambourg"},
        {"name": "Schenker AG (DB Schenker)", "sector": "Transport & Logistique", "cities": "Essen, Francfort"},
        
        # Santé & Pharma
        {"name": "Charité - Universitätsmedizin Berlin", "sector": "Santé & Hôpital", "cities": "Berlin"},
        {"name": "Universitätsklinikum Heidelberg", "sector": "Santé & Hôpital", "cities": "Heidelberg"},
        {"name": "Universitätsklinikum München", "sector": "Santé & Hôpital", "cities": "Munich"},
        {"name": "Universitätsklinikum Hamburg-Eppendorf", "sector": "Santé & Hôpital", "cities": "Hambourg"},
        {"name": "Asklepios Kliniken", "sector": "Santé & Hôpital", "cities": "Hambourg, Munich"},
        {"name": "Helios Kliniken", "sector": "Santé & Hôpital", "cities": "Berlin, Erfurt, Schwerin"},
        {"name": "Sana Kliniken AG", "sector": "Santé & Hôpital", "cities": "Ismaning, Stuttgart, Düsseldorf"},
        {"name": "Siemens Healthineers", "sector": "Santé & Technologie", "cities": "Erlangen, Forchheim"},
        {"name": "Fresenius SE & Co. KGaA", "sector": "Santé & Hôpital", "cities": "Bad Homburg"},
        {"name": "AOK - Die Gesundheitskasse", "sector": "Assurance Santé", "cities": "Berlin, Stuttgart, Munich"},
        {"name": "Barmer", "sector": "Assurance Santé", "cities": "Wuppertal, Berlin"},
        {"name": "Techniker Krankenkasse (TK)", "sector": "Assurance Santé", "cities": "Hambourg, Francfort"},
        
        # Commerce, Banque & Finance
        {"name": "Allianz SE", "sector": "Banque, Assurance & Finance", "cities": "Munich, Stuttgart, Francfort"},
        {"name": "Munich Re", "sector": "Banque, Assurance & Finance", "cities": "Munich"},
        {"name": "Deutsche Bank AG", "sector": "Banque, Assurance & Finance", "cities": "Francfort, Berlin, Düsseldorf"},
        {"name": "Commerzbank AG", "sector": "Banque, Assurance & Finance", "cities": "Francfort, Hambourg, Munich"},
        {"name": "Sparkasse", "sector": "Banque, Assurance & Finance", "cities": "Berlin, Cologne, Stuttgart, Munich"},
        {"name": "Volksbanken Raiffeisenbanken", "sector": "Banque, Assurance & Finance", "cities": "Francfort, Munich, Hambourg"},
        {"name": "ALDI SÜD", "sector": "Commerce & Distribution", "cities": "Mülheim an der Ruhr, Munich, Stuttgart"},
        {"name": "ALDI NORD", "sector": "Commerce & Distribution", "cities": "Essen, Berlin, Hambourg"},
        {"name": "Lidl (Schwarz Gruppe)", "sector": "Commerce & Distribution", "cities": "Neckarsulm, Berlin, Munich"},
        {"name": "REWE Group", "sector": "Commerce & Distribution", "cities": "Cologne, Francfort, Munich"},
        {"name": "Edeka", "sector": "Commerce & Distribution", "cities": "Hambourg, Munich, Cologne"},
        {"name": "Metro AG", "sector": "Commerce & Distribution", "cities": "Düsseldorf"},
        {"name": "Dr. Oetker KG", "sector": "Alimentaire & Distribution", "cities": "Bielefeld"},
        {"name": "Adidas AG", "sector": "Commerce & Mode", "cities": "Herzogenaurach"},
        {"name": "Bertelsmann SE & Co. KGaA", "sector": "Médias & Services", "cities": "Gütersloh, Cologne, Berlin"},
        
        # Services & Énergie
        {"name": "E.ON SE", "sector": "Énergie & Services", "cities": "Essen, Hanovre, Munich"},
        {"name": "RWE AG", "sector": "Énergie & Services", "cities": "Essen, Cologne"},
        {"name": "EnBW Energie Baden-Württemberg", "sector": "Énergie & Services", "cities": "Karlsruhe, Stuttgart"},
        {"name": "TÜV SÜD", "sector": "Services & Certification", "cities": "Munich, Stuttgart"},
        {"name": "TÜV Rheinland", "sector": "Services & Certification", "cities": "Cologne, Berlin"},
        {"name": "TÜV Nord", "sector": "Services & Certification", "cities": "Hanovre, Hambourg"},
        {"name": "DEKRA SE", "sector": "Services & Certification", "cities": "Stuttgart"},
        {"name": "Fraunhofer-Gesellschaft", "sector": "Recherche & Services", "cities": "Munich, Stuttgart, Dresde"},
        {"name": "Max-Planck-Gesellschaft", "sector": "Recherche & Services", "cities": "Munich, Göttingen, Heidelberg"},
        {"name": "DLR", "sector": "Recherche & Aérospatiale", "cities": "Cologne, Munich, Stuttgart, Berlin"},
    ]

    # Récupérer les offres actives en base regroupées par entreprise
    db_counts = AusbildungOffer.objects.filter(is_active=True).values("company").annotate(
        count=Count("id")
    )
    counts_map = {item["company"].lower().strip(): item["count"] for item in db_counts}

    # Croiser les entreprises statiques avec les offres actives en base de données
    for c in COMPANIES:
        name_lower = c["name"].lower().strip()
        c["count"] = 0
        for db_name, count in counts_map.items():
            if db_name in name_lower or name_lower in db_name:
                c["count"] = max(c["count"], count)

    # Filtrer par mots-clés
    if search_q:
        q_lower = search_q.lower()
        COMPANIES = [
            c for c in COMPANIES
            if q_lower in c["name"].lower() or q_lower in c["sector"].lower() or q_lower in c["cities"].lower()
        ]

    context = {
        "companies": COMPANIES,
        "search_q": search_q,
        "total_companies": len(COMPANIES),
    }
    return render(request, "germany_opportunities/top_companies.html", context)


def premium_pricing(request):
    """Page de tarification premium Allemagne (SaaS landing page)."""
    return render(request, "germany_opportunities/premium_pricing.html")



def check_user_has_paid_edu_subscription(user) -> bool:
    """Helper local pour vérifier l'abonnement premium allemand d'un candidat."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if hasattr(user, "profile") and user.profile.plan in ["pro", "enterprise"]:
        return True
    try:
        from accounts.models import AppSubscription
        sub = AppSubscription.get_active_for_user(user, "allemand")
        if sub and sub.is_active and not sub.plan.is_free:
            return True
    except Exception:
        pass
    return False


@login_required
def interview_simulator_hub(request):
    """Affiche la liste des simulations de l'utilisateur et permet d'en lancer une nouvelle."""
    from .models import AusbildungInterviewSimulation
    from django.contrib import messages

    is_premium = check_user_has_paid_edu_subscription(request.user)
    simulations = AusbildungInterviewSimulation.objects.filter(user=request.user).order_by("-created_at")

    # Secteurs d'activité possibles
    SECTOR_CHOICES = list(AusbildungOffer.SECTOR_CHOICES) + [("autre", "Autre / Candidature Spontanée")]

    context = {
        "simulations":    simulations,
        "sector_choices": SECTOR_CHOICES,
        "is_premium":      is_premium,
    }
    return render(request, "germany_opportunities/interview_simulator_hub.html", context)


@login_required
@require_POST
def start_interview_simulation(request):
    """Démarre une nouvelle simulation d'entretien."""
    from .models import AusbildungInterviewSimulation
    from ai_engine.services.llm_service import call_llm
    from django.contrib import messages

    sector = request.POST.get("sector", "autre").strip()
    is_premium = check_user_has_paid_edu_subscription(request.user)

    # Restriction Premium
    if not is_premium and sector != "autre":
        messages.warning(request, "L'accès aux simulations par secteur d'activité est réservé aux abonnés Premium. Vous pouvez essayer le mode d'essai gratuit.")
        return redirect("germany_opportunities:interview_simulator_hub")

    # Création de la simulation
    sim = AusbildungInterviewSimulation.objects.create(
        user=request.user,
        sector=sector,
        messages=[]
    )

    # Premier appel Gemini pour la question d'intro
    sector_display = dict(list(AusbildungOffer.SECTOR_CHOICES) + [("autre", "Autre / Candidature Spontanée")]).get(sector, sector)
    system_prompt = (
        "Du bist Herr Schmidt, un directeur des ressources humaines (DRH) allemand très expérimenté "
        f"qui recrute pour une Ausbildung dans le secteur : {sector_display}.\n"
        "Tu mènes un entretien en ALLEMAND avec un candidat international.\n"
        "Présente-toi brièvement et poliment en allemand, souhaite la bienvenue au candidat, "
        "et pose-lui la première question classique (ex: lui demander de se présenter brièvement "
        "et d'expliquer pourquoi il s'intéresse à ce métier).\n"
        "Parle UNIQUEMENT en allemand professionnel. Ne mets aucune traduction."
    )

    try:
        first_question = call_llm(system_prompt, "Démarrer l'entretien.")
    except Exception:
        first_question = ""

    if not first_question:
        first_question = "Guten Tag. Ich bin Herr Schmidt. Herzlich willkommen zu unserem Gespräch. Bitte stellen Sie sich kurz vor und erklären Sie, warum Sie sich für diese Ausbildung interessieren."

    sim.messages = [{"role": "assistant", "content": first_question}]
    sim.save()

    return redirect("germany_opportunities:interview_simulation_detail", pk=sim.pk)


@login_required
def interview_simulation_detail(request, pk):
    """Salle de simulation d'entretien interactif (chat)."""
    from .models import AusbildungInterviewSimulation
    sim = get_object_or_404(AusbildungInterviewSimulation, pk=pk, user=request.user)
    
    sector_display = dict(list(AusbildungOffer.SECTOR_CHOICES) + [("autre", "Autre / Candidature Spontanée")]).get(sim.sector, sim.sector)

    # Rendu du feedback structuré s'il est déjà évalué
    feedback_structured = {}
    if sim.is_completed and sim.feedback:
        raw = sim.feedback
        for key in ["SCORE", "CORRECTIONS", "VOCABULAIRE", "RECOMMANDATIONS"]:
            marker = f"=== {key} ==="
            if marker in raw:
                try:
                    parts = raw.split(marker)[1]
                    if "===" in parts:
                        parts = parts.split("===")[0]
                    feedback_structured[key.lower()] = parts.strip()
                except Exception:
                    pass

    context = {
        "simulation": sim,
        "sector_display": sector_display,
        "feedback_structured": feedback_structured,
    }
    return render(request, "germany_opportunities/interview_simulator_detail.html", context)


@login_required
@require_POST
def interview_simulation_message(request, pk):
    """Réception d'un message du candidat et relance en allemand par Herr Schmidt."""
    from .models import AusbildungInterviewSimulation
    from ai_engine.services.llm_service import call_llm

    sim = get_object_or_404(AusbildungInterviewSimulation, pk=pk, user=request.user)
    if sim.is_completed:
        return JsonResponse({"status": "error", "message": "Cet entretien est déjà terminé."})

    message = request.POST.get("message", "").strip()
    if not message:
        return JsonResponse({"status": "error", "message": "Message vide."})

    # Ajouter le message utilisateur
    sim.messages.append({"role": "user", "content": message})
    sim.save(update_fields=["messages"])

    # Reconstruire le fil de discussion pour l'IA
    history_str = ""
    for m in sim.messages:
        role_name = "Recruteur (Herr Schmidt)" if m["role"] == "assistant" else "Candidat"
        history_str += f"{role_name} : {m['content']}\n\n"

    sector_display = dict(list(AusbildungOffer.SECTOR_CHOICES) + [("autre", "Autre / Candidature Spontanée")]).get(sim.sector, sim.sector)
    system_prompt = (
        "Du bist Herr Schmidt, un recruteur allemand expérimenté qui mène un entretien d'embauche "
        f"en ALLEMAND dans le secteur : {sector_display}.\n"
        "Voici l'historique de notre conversation actuelle. Réagis brièvement à la dernière réponse "
        "du candidat, puis pose-lui la question suivante dans l'ordre d'un entretien classique "
        "(par exemple, sur ses motivations, son expérience d'équipe, ou son adaptation en Allemagne).\n"
        "Parle UNIQUEMENT en allemand professionnel. Ne pose JAMAIS deux questions à la fois. "
        "Pas de traductions ou de remarques hors rôle."
    )

    try:
        ai_response = call_llm(system_prompt, history_str)
    except Exception:
        ai_response = ""

    if not ai_response:
        ai_response = "Ich verstehe. Können Sie mir bitte erklären, wie Sie in stressigen Situationen die Ruhe bewahren?"

    # Enregistrer la question du recruteur
    sim.messages.append({"role": "assistant", "content": ai_response})
    sim.save(update_fields=["messages"])

    return JsonResponse({"status": "success", "ai_response": ai_response})


@login_required
@require_POST
def interview_simulation_evaluate(request, pk):
    """Clôture de l'entretien et appel à Gemini pour le rapport final (Score + Corrections en FR)."""
    from .models import AusbildungInterviewSimulation
    from ai_engine.services.llm_service import call_llm
    import re

    sim = get_object_or_404(AusbildungInterviewSimulation, pk=pk, user=request.user)
    if sim.is_completed:
        return JsonResponse({"status": "error", "message": "Déjà évalué."})

    # Reconstruire le fil de discussion
    history_str = ""
    for m in sim.messages:
        role_name = "Recruteur (Herr Schmidt)" if m["role"] == "assistant" else "Candidat"
        history_str += f"{role_name} : {m['content']}\n\n"

    sector_display = dict(list(AusbildungOffer.SECTOR_CHOICES) + [("autre", "Autre / Candidature Spontanée")]).get(sim.sector, sim.sector)
    system_prompt = (
        "Tu es un expert RH allemand et un coach de langue spécialisé dans le recrutement de candidats "
        f"internationaux pour des Ausbildung en Allemagne dans le secteur : {sector_display}.\n"
        "Tu analyses l'historique complet d'un entretien d'embauche simulé.\n"
        "Fournis une évaluation rigoureuse, constructive et rédigée EN FRANÇAIS.\n\n"
        "Format impératif (respecte exactement ces balises et ne renvoie rien d'autre) :\n\n"
        "=== SCORE ===\n"
        "[Un nombre entier entre 0 et 100 uniquement représentant le niveau global du candidat]\n\n"
        "=== CORRECTIONS ===\n"
        "[Phrases originales erronées ou maladroites en allemand -> corrections en allemand : explications détaillées en français]\n\n"
        "=== VOCABULAIRE ===\n"
        "[Mots et expressions d'allemand professionnel utiles pour ce secteur d'activité]\n\n"
        "=== RECOMMANDATIONS ===\n"
        "[Conseils stratégiques généraux en français pour s'améliorer]"
    )

    try:
        evaluation_text = call_llm(system_prompt, history_str)
    except Exception as exc:
        evaluation_text = f"=== SCORE ===\n50\n\n=== CORRECTIONS ===\nErreur lors de la génération : {exc}\n\n=== VOCABULAIRE ===\nNon disponible\n\n=== RECOMMANDATIONS ===\nRéessayez ultérieurement."

    # Parser le score
    score = 65
    if "=== SCORE ===" in evaluation_text:
        try:
            score_part = evaluation_text.split("=== SCORE ===")[1].split("===")[0].strip()
            digits = re.findall(r'\d+', score_part)
            if digits:
                score = int(digits[0])
        except Exception:
            pass

    sim.score = score
    sim.feedback = evaluation_text
    sim.is_completed = True
    sim.save()

    return JsonResponse({
        "status": "success",
        "score": score,
        "feedback": evaluation_text
    })


