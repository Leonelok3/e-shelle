"""
api/views.py — API REST E-Shelle (DRF)
Endpoints JSON pour les opérations AJAX du frontend.
"""
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from django.urls import reverse
import urllib.parse


@require_GET
def search(request):
    """Recherche globale : formations + produits + fiches business."""
    q = request.GET.get("q", "").strip()
    results = []

    if len(q) >= 2:
        from formations.models import Formation
        from boutique.models import Produit
        from business.models import BusinessProfile

        formations = Formation.objects.filter(
            is_published=True
        ).filter(Q(titre__icontains=q) | Q(description__icontains=q))[:5]

        produits = Produit.objects.filter(
            is_published=True
        ).filter(Q(titre__icontains=q) | Q(description__icontains=q))[:5]

        businesses = BusinessProfile.objects.filter(is_active=True).filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(promo_headline__icontains=q)
            | Q(promo_offer__icontains=q)
            | Q(city__icontains=q)
            | Q(district__icontains=q)
        )[:6]

        for f in formations:
            results.append({
                "type":  "Formation",
                "title": f.titre,
                "url":   f"/formations/{f.slug}/",
            })
        for p in produits:
            results.append({
                "type":  "Produit",
                "title": p.titre,
                "url":   f"/boutique/{p.slug}/",
            })
        for business in businesses:
            results.append({
                "type": business.get_module_display(),
                "title": business.promo_headline or business.name,
                "url": business.get_absolute_url(),
            })

    response = {"results": results, "q": q}
    if q and not results:
        google_q = urllib.parse.quote_plus(f"{q} Cameroun")
        response["unmet_search"] = {
            "capture_url": f"{reverse('business:unmet_search_express')}?q={urllib.parse.quote(q)}&source=header_search",
            "chat_url": f"{reverse('chat:home')}?q={urllib.parse.quote(q)}",
            "google_url": f"https://www.google.com/search?q={google_q}",
            "facebook_url": f"https://www.facebook.com/search/top?q={urllib.parse.quote_plus(q)}",
            "message": "Aucun resultat parfait. E-Shelle peut demander au reseau ou verifier des pistes externes.",
        }
    return JsonResponse(response)


@require_GET
def notifications_count(request):
    """Nombre de notifications non lues pour l'utilisateur connecté."""
    if not request.user.is_authenticated:
        return JsonResponse({"count": 0})

    from dashboard.models import Notification
    count = Notification.objects.filter(
        destinataire=request.user, lue=False
    ).count()
    return JsonResponse({"count": count})
