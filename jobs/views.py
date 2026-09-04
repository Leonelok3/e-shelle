from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .forms import CandidatureJobForm, OffreJobForm
from .models import OffreJob, SecteurJob, VilleJob, CanadaJobOffer


def check_user_has_french_premium(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        from accounts.models import AppSubscription
        sub = AppSubscription.get_active_for_user(user, "prep")
        if sub and sub.is_active and not sub.plan.is_free:
            return True
    except Exception:
        pass
    return False


def accueil(request):
    offres_featured = OffreJob.objects.filter(is_active=True, is_featured=True).select_related("ville", "secteur")[:6]
    offres_recentes = OffreJob.objects.filter(is_active=True).select_related("ville", "secteur")[:8]
    context = {
        "offres_featured": offres_featured,
        "offres_recentes": offres_recentes,
        "secteurs": SecteurJob.objects.filter(active=True)[:10],
        "villes": VilleJob.objects.filter(active=True)[:10],
        "nb_offres": OffreJob.objects.filter(is_active=True).count(),
        "nb_villes": VilleJob.objects.filter(active=True, offres__is_active=True).distinct().count(),
    }
    return render(request, "jobs/accueil.html", context)


def catalogue(request):
    offres = OffreJob.objects.filter(is_active=True).select_related("ville", "secteur")
    q = request.GET.get("q", "").strip()
    ville_slug = request.GET.get("ville", "")
    secteur_slug = request.GET.get("secteur", "")
    contrat = request.GET.get("contrat", "")

    if q:
        offres = offres.filter(
            Q(titre__icontains=q) |
            Q(entreprise__icontains=q) |
            Q(description__icontains=q) |
            Q(quartier__icontains=q)
        )
    if ville_slug:
        offres = offres.filter(ville__slug=ville_slug)
    if secteur_slug:
        offres = offres.filter(secteur__slug=secteur_slug)
    if contrat:
        offres = offres.filter(type_contrat=contrat)

    context = {
        "offres": offres.distinct(),
        "secteurs": SecteurJob.objects.filter(active=True),
        "villes": VilleJob.objects.filter(active=True),
        "q": q,
        "ville_slug": ville_slug,
        "secteur_slug": secteur_slug,
        "contrat": contrat,
        "contrats": OffreJob.TypeContrat.choices,
        "nb_results": offres.count(),
    }
    return render(request, "jobs/catalogue.html", context)


def detail(request, slug):
    offre = get_object_or_404(OffreJob.objects.select_related("ville", "secteur"), slug=slug, is_active=True)
    OffreJob.objects.filter(pk=offre.pk).update(vues=offre.vues + 1)
    similaires = OffreJob.objects.filter(is_active=True, secteur=offre.secteur).exclude(pk=offre.pk).select_related("ville", "secteur")[:4]

    if request.method == "POST":
        form = CandidatureJobForm(request.POST, request.FILES)
        if form.is_valid():
            candidature = form.save(commit=False)
            candidature.offre = offre
            candidature.save()
            messages.success(request, "Votre candidature a ete envoyee.")
            return redirect("jobs:detail", slug=offre.slug)
        messages.error(request, "Verifiez les informations du formulaire.")
    else:
        form = CandidatureJobForm()

    return render(request, "jobs/detail.html", {"offre": offre, "form": form, "similaires": similaires})


def publier(request):
    if request.method == "POST":
        form = OffreJobForm(request.POST)
        if form.is_valid():
            offre = form.save(commit=False)
            if request.user.is_authenticated:
                offre.auteur = request.user
            offre.is_active = False
            offre.save()
            messages.success(request, "Offre recue. Elle sera publiee apres verification.")
            return redirect("jobs:accueil")
        messages.error(request, "Verifiez les informations de l'offre.")
    else:
        form = OffreJobForm()
    return render(request, "jobs/publier.html", {"form": form})


def canada_jobs(request):
    has_premium = check_user_has_french_premium(request.user)
    offres = CanadaJobOffer.objects.filter(is_active=True).order_by("-source_posted_date", "-fetched_at")
    q = request.GET.get("q", "").strip()
    province = request.GET.get("province", "").strip()
    city = request.GET.get("city", "").strip()

    if q:
        offres = offres.filter(
            Q(title__icontains=q) |
            Q(company__icontains=q) |
            Q(description__icontains=q)
        )
    if province:
        offres = offres.filter(province__icontains=province)
    if city:
        offres = offres.filter(city__icontains=city)

    # Obtenir la liste des provinces uniques pour le filtre
    provinces = CanadaJobOffer.objects.filter(is_active=True).values_list("province", flat=True).distinct()
    provinces = sorted(list({p.strip() for p in provinces if p}))

    context = {
        "offres": offres,
        "q": q,
        "province": province,
        "city": city,
        "provinces": provinces,
        "total_offers": offres.count(),
        "has_premium": has_premium,
    }
    return render(request, "jobs/canada_jobs.html", context)


def canada_scholarships(request):
    """
    Affiche la liste des bourses d'études au Canada trouvées par l'IA.
    """
    has_premium = check_user_has_french_premium(request.user)
    from .models import CanadaScholarship
    scholarships = CanadaScholarship.objects.filter(is_active=True)
    q = request.GET.get("q", "").strip()
    provider = request.GET.get("provider", "").strip()

    if q:
        scholarships = scholarships.filter(
            Q(title__icontains=q) |
            Q(provider__icontains=q) |
            Q(description__icontains=q) |
            Q(eligibility__icontains=q)
        )
    if provider:
        scholarships = scholarships.filter(provider__icontains=provider)

    providers = CanadaScholarship.objects.filter(is_active=True).values_list("provider", flat=True).distinct()
    providers = sorted(list({p.strip() for p in providers if p}))

    context = {
        "scholarships": scholarships,
        "q": q,
        "provider": provider,
        "providers": providers,
        "total_scholarships": scholarships.count(),
        "has_premium": has_premium,
    }
    return render(request, "jobs/canada_scholarships.html", context)


def canada_visitor_opps(request):
    """
    Affiche la liste des opportunités de visa visiteur Canada (conférences, séminaires, etc.).
    """
    has_premium = check_user_has_french_premium(request.user)
    from .models import CanadaVisitorOpportunity
    opps = CanadaVisitorOpportunity.objects.filter(is_active=True)
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()

    if q:
        opps = opps.filter(
            Q(title__icontains=q) |
            Q(organizer__icontains=q) |
            Q(description__icontains=q)
        )
    if location:
        opps = opps.filter(location__icontains=location)

    locations = CanadaVisitorOpportunity.objects.filter(is_active=True).values_list("location", flat=True).distinct()
    locations = sorted(list({loc.strip() for loc in locations if loc}))

    context = {
        "opps": opps,
        "q": q,
        "location": location,
        "locations": locations,
        "total_opps": opps.count(),
        "has_premium": has_premium,
    }
    return render(request, "jobs/canada_visitor_opps.html", context)


def canada_news(request):
    """
    Actualités, communiqués officiels, lois sur l'immigration et tirages (Express Entry/Arrima) concernant le Canada.
    """
    has_premium = check_user_has_french_premium(request.user)
    from .models import CanadaNews
    
    news_list = CanadaNews.objects.filter(is_active=True).order_by("-fetched_at")
    
    category = request.GET.get("category", "").strip()
    q = request.GET.get("q", "").strip()
    
    if category:
        news_list = news_list.filter(category=category)
    if q:
        news_list = news_list.filter(
            Q(title__icontains=q) |
            Q(summary__icontains=q)
        )
        
    categories = CanadaNews.objects.filter(is_active=True).values_list("category", flat=True).distinct()
    categories = sorted(list({c.strip() for c in categories if c}))
    
    context = {
        "news_list": news_list,
        "q": q,
        "category": category,
        "categories": categories,
        "total_news": news_list.count(),
        "has_premium": has_premium,
    }
    return render(request, "jobs/canada_news.html", context)


import threading
import logging
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger(__name__)

def cron_webhook(request):
    """
    Webhook pour Cron-Job.org permettant de lancer l'importation et la mise à jour
    quotidienne des opportunités d'emploi Canada et Allemagne en tâche de fond.
    """
    from django.http import JsonResponse
    # Vérification sécurisée du jeton d'accès
    secret_token = getattr(settings, "CRON_SECRET", "eshelle_secret_cron_2026")
    token_received = request.GET.get("token")

    if not token_received or token_received != secret_token:
        return JsonResponse({"status": "error", "message": "Accès refusé. Jeton invalide."}, status=403)

    def run_daily_imports_in_background():
        logger.info("[CRON] Début du traitement en tâche de fond...")
        
        # 1. Canada - Offres d'emploi
        try:
            logger.info("[CRON] Lancement de fetch_canada_jobs...")
            call_command("fetch_canada_jobs")
        except Exception as e:
            logger.error(f"[CRON] Erreur fetch_canada_jobs : {e}")

        # 2. Canada - Bourses d'études
        try:
            logger.info("[CRON] Lancement de fetch_canada_scholarships...")
            call_command("fetch_canada_scholarships")
        except Exception as e:
            logger.error(f"[CRON] Erreur fetch_canada_scholarships : {e}")

        # 3. Canada - Opportunités Visiteur
        try:
            logger.info("[CRON] Lancement de fetch_canada_visitor_opps...")
            call_command("fetch_canada_visitor_opps")
        except Exception as e:
            logger.error(f"[CRON] Erreur fetch_canada_visitor_opps : {e}")

        # 4. Canada - Actualités
        try:
            logger.info("[CRON] Lancement de fetch_canada_news...")
            call_command("fetch_canada_news")
        except Exception as e:
            logger.error(f"[CRON] Erreur fetch_canada_news : {e}")

        # 5. Canada - Vérification des liens & expirations
        try:
            logger.info("[CRON] Lancement de verify_links_and_deadlines...")
            call_command("verify_links_and_deadlines")
        except Exception as e:
            logger.error(f"[CRON] Erreur verify_links_and_deadlines : {e}")

        # 6. Allemagne - Ausbildung & IA
        try:
            logger.info("[CRON] Lancement de fetch_ausbildung_offers...")
            from germany_opportunities.tasks import fetch_ausbildung_offers, enrich_offers_with_ai
            fetch_ausbildung_offers()
            logger.info("[CRON] Lancement de enrich_offers_with_ai...")
            enrich_offers_with_ai()
        except Exception as e:
            logger.error(f"[CRON] Erreur tasks Allemagne : {e}")

        logger.info("[CRON] Fin de toutes les importations matinales.")

    # Lancement dans un thread séparé pour répondre instantanément à Cron-Job.org et éviter un timeout
    threading.Thread(target=run_daily_imports_in_background, daemon=True).start()

    return JsonResponse({
        "status": "success",
        "message": "Importations quotidiennes d'opportunités (Canada et Allemagne) lancées en tâche de fond."
    })




