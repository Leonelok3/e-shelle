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

    offers = AusbildungOffer.objects.filter(is_active=True)

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

    scholarships = ScholarshipOpportunity.objects.filter(is_active=True).order_by("deadline")[:6]
    has_active_filters = any([sector, level, city_q, region_q, search_q])

    context = {
        "offers":         offers[:60],
        "scholarships":   scholarships,
        "sector_labels":  SECTOR_LABELS,
        "active_sector":  sector,
        "active_level":   level,
        "active_region":  region_q,
        "active_sort":    sort,
        "city_q":         city_q,
        "search_q":       search_q,
        "bookmarked_ids": bookmarked_ids,
        "total_offers":   AusbildungOffer.objects.filter(is_active=True).count(),
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
