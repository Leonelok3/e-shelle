from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CandidatureJobForm, OffreJobForm
from .models import OffreJob, SecteurJob, VilleJob, CanadaJobOffer


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
    offres = CanadaJobOffer.objects.filter(is_active=True)
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
    }
    return render(request, "jobs/canada_jobs.html", context)


def canada_scholarships(request):
    """
    Affiche la liste des bourses d'études au Canada trouvées par l'IA.
    """
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
    }
    return render(request, "jobs/canada_scholarships.html", context)


