"""gaz/views.py — E-Shelle Gaz"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import VilleGaz, QuartierGaz, MarqueGaz, DepotGaz, AvisDepot
from .forms import DepotGazForm


def accueil(request):
    """Page d'accueil — hero + depots mis en avant + selection ville."""
    villes    = VilleGaz.objects.filter(active=True).prefetch_related("depots")
    featured  = DepotGaz.objects.filter(is_active=True, is_featured=True).select_related("ville", "quartier").prefetch_related("marques")[:6]
    verified  = DepotGaz.objects.filter(is_active=True, is_verified=True).select_related("ville", "quartier").prefetch_related("marques")[:8]
    recents   = DepotGaz.objects.filter(is_active=True).select_related("ville", "quartier").prefetch_related("marques").order_by("-created_at")[:6]
    nb_total  = DepotGaz.objects.filter(is_active=True).count()
    nb_villes = VilleGaz.objects.filter(active=True, depots__is_active=True).distinct().count()

    context = {
        "villes":    villes,
        "featured":  featured,
        "verified":  verified,
        "recents":   recents,
        "nb_total":  nb_total,
        "nb_villes": nb_villes,
    }
    return render(request, "gaz/accueil.html", context)


@login_required
def creer_depot(request):
    """Creation rapide d'un depot de gaz par un client."""
    if request.method == "POST":
        form = DepotGazForm(request.POST, request.FILES)
        if form.is_valid():
            depot = form.save(commit=False)
            depot.gerant = request.user
            # Auto-active et verifie par defaut pour affichage immediat sur la plateforme
            depot.is_active = True
            depot.is_verified = True
            depot.save()
            form.save_m2m()
            return redirect("gaz:detail", slug=depot.slug)
    else:
        form = DepotGazForm()
    
    return render(request, "gaz/creer_depot.html", {"form": form})


def catalogue(request):
    """Liste des depots avec filtres ville / quartier / marque / livraison rapide."""
    depots = DepotGaz.objects.filter(is_active=True).select_related("ville", "quartier").prefetch_related("marques")
    villes  = VilleGaz.objects.filter(active=True)
    marques = MarqueGaz.objects.filter(active=True)

    # Filtres
    ville_slug   = request.GET.get("ville", "")
    quartier_id  = request.GET.get("quartier", "")
    marque_slug  = request.GET.get("marque", "")
    rapide       = request.GET.get("rapide", "")
    nuit         = request.GET.get("nuit", "")
    taille       = request.GET.get("taille", "")
    q            = request.GET.get("q", "").strip()

    ville_active   = None
    quartiers_list = []

    if ville_slug:
        try:
            ville_active   = VilleGaz.objects.get(slug=ville_slug)
            quartiers_list = QuartierGaz.objects.filter(ville=ville_active, active=True)
            depots         = depots.filter(ville=ville_active)
        except VilleGaz.DoesNotExist:
            pass

    if quartier_id:
        depots = depots.filter(quartier_id=quartier_id)

    if marque_slug:
        depots = depots.filter(marques__slug=marque_slug)

    if rapide:
        depots = depots.filter(livraison_rapide=True)

    if nuit:
        depots = depots.filter(livraison_nuit=True)

    if taille:
        depots = depots.filter(tailles__contains=taille)

    if q:
        depots = depots.filter(
            Q(nom__icontains=q) |
            Q(adresse__icontains=q) |
            Q(zone_livraison__icontains=q) |
            Q(quartier__nom__icontains=q)
        )

    depots = depots.distinct().order_by("-is_featured", "-is_verified", "nom")

    context = {
        "depots":        depots,
        "villes":        villes,
        "marques":       marques,
        "quartiers_list": quartiers_list,
        "ville_active":  ville_active,
        "ville_slug":    ville_slug,
        "quartier_id":   quartier_id,
        "marque_slug":   marque_slug,
        "rapide":        rapide,
        "nuit":          nuit,
        "taille":        taille,
        "q":             q,
        "nb_results":    depots.count(),
        "tailles_choices": [
            ("6kg", "6 kg"), ("12kg", "12 kg"), ("15kg", "15 kg"),
            ("25kg", "25 kg"), ("38kg", "38 kg"),
        ],
    }
    return render(request, "gaz/catalogue.html", context)


def detail(request, slug):
    """Page detail d'un depot avec contacts WhatsApp + appel + avis."""
    depot  = get_object_or_404(DepotGaz, slug=slug, is_active=True)
    avis   = depot.avis.select_related("auteur").order_by("-created_at")[:10]

    # Depots similaires (meme ville)
    similaires = DepotGaz.objects.filter(
        ville=depot.ville, is_active=True
    ).exclude(pk=depot.pk).select_related("ville").prefetch_related("marques")[:4]

    # Avis de l'utilisateur connecte
    mon_avis = None
    if request.user.is_authenticated:
        mon_avis = AvisDepot.objects.filter(depot=depot, auteur=request.user).first()

    # Soumission d'un avis
    if request.method == "POST" and request.user.is_authenticated:
        note = int(request.POST.get("note", 0))
        commentaire = request.POST.get("commentaire", "").strip()
        if 1 <= note <= 5:
            AvisDepot.objects.update_or_create(
                depot=depot, auteur=request.user,
                defaults={"note": note, "commentaire": commentaire}
            )
            depot.refresh_from_db()
            mon_avis = AvisDepot.objects.get(depot=depot, auteur=request.user)

    context = {
        "depot":      depot,
        "avis":       avis,
        "similaires": similaires,
        "mon_avis":   mon_avis,
    }
    return render(request, "gaz/detail.html", context)
