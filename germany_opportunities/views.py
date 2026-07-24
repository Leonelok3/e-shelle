from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Case, When, Value, IntegerField

from .models import AusbildungOffer, ScholarshipOpportunity, UserOpportunityBookmark


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
    }
    return render(request, "germany_opportunities/catalogue.html", context)


def offer_detail(request, pk):
    """Detail d'une offre Ausbildung."""
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

