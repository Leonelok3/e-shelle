from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DemandeSanteForm, ProduitSanteForm, ProfessionnelSanteForm
from .models import CategorieSante, DemandeSante, ProduitSante, ProfessionnelSante, VilleSante


def _produits_actifs():
    return ProduitSante.objects.filter(is_active=True)


def _pros_actifs():
    return ProfessionnelSante.objects.filter(is_active=True)


def accueil(request):
    produits_vedette = _produits_actifs().filter(is_featured=True).select_related("ville", "categorie")[:8]
    pros_vedette = _pros_actifs().filter(is_featured=True).select_related("ville")[:6]
    categories = CategorieSante.objects.filter(active=True)[:12]
    villes = VilleSante.objects.filter(active=True)
    stats = {
        "produits": _produits_actifs().count(),
        "pros": _pros_actifs().count(),
        "villes": villes.count(),
        "demandes": DemandeSante.objects.filter(is_active=True).count(),
    }
    return render(request, "sante/accueil.html", {
        "produits_vedette": produits_vedette,
        "pros_vedette": pros_vedette,
        "categories": categories,
        "villes": villes,
        "stats": stats,
    })


def produits(request):
    q = request.GET.get("q", "").strip()
    ville = request.GET.get("ville", "")
    cat = request.GET.get("cat", "")
    type_produit = request.GET.get("type", "")
    livraison = request.GET.get("livraison", "")

    produits_qs = _produits_actifs().select_related("ville", "categorie")
    if q:
        produits_qs = produits_qs.filter(Q(titre__icontains=q) | Q(description__icontains=q) | Q(vendeur_nom__icontains=q))
    if ville:
        produits_qs = produits_qs.filter(ville__slug=ville)
    if cat:
        produits_qs = produits_qs.filter(categorie__slug=cat)
    if type_produit:
        produits_qs = produits_qs.filter(type_produit=type_produit)
    if livraison:
        produits_qs = produits_qs.filter(livraison=True)

    return render(request, "sante/produits.html", {
        "produits": produits_qs,
        "villes": VilleSante.objects.filter(active=True),
        "categories": CategorieSante.objects.filter(active=True, type_categorie__in=[
            CategorieSante.TypeCategorie.PRODUIT,
            CategorieSante.TypeCategorie.SPECIALITE,
        ]),
        "types": ProduitSante.TypeProduit.choices,
        "q": q,
        "ville": ville,
        "cat": cat,
        "type_produit": type_produit,
        "livraison": livraison,
        "nb_results": produits_qs.count(),
    })


def detail_produit(request, slug):
    produit = get_object_or_404(_produits_actifs().select_related("ville", "categorie"), slug=slug)
    ProduitSante.objects.filter(pk=produit.pk).update(vues=produit.vues + 1)
    similaires = _produits_actifs().filter(type_produit=produit.type_produit).exclude(pk=produit.pk).select_related("ville", "categorie")[:4]
    return render(request, "sante/detail_produit.html", {"produit": produit, "similaires": similaires})


def publier_produit(request):
    if request.method == "POST":
        form = ProduitSanteForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save(commit=False)
            if request.user.is_authenticated:
                produit.auteur = request.user
            produit.is_active = False
            produit.save()
            messages.success(request, "Produit reçu. Il sera publié après vérification.")
            return redirect("sante:accueil")
        messages.error(request, "Vérifiez les informations du produit.")
    else:
        form = ProduitSanteForm()
    return render(request, "sante/publier_produit.html", {"form": form})


def professionnels(request):
    q = request.GET.get("q", "").strip()
    ville = request.GET.get("ville", "")
    specialite = request.GET.get("specialite", "")
    urgence = request.GET.get("urgence", "")
    domicile = request.GET.get("domicile", "")

    pros = _pros_actifs().select_related("ville").prefetch_related("specialites")
    if q:
        pros = pros.filter(Q(nom__icontains=q) | Q(description__icontains=q) | Q(quartier__icontains=q))
    if ville:
        pros = pros.filter(ville__slug=ville)
    if specialite:
        pros = pros.filter(specialites__slug=specialite)
    if urgence:
        pros = pros.filter(urgence=True)
    if domicile:
        pros = pros.filter(consultation_domicile=True)

    return render(request, "sante/professionnels.html", {
        "pros": pros.distinct(),
        "villes": VilleSante.objects.filter(active=True),
        "specialites": CategorieSante.objects.filter(active=True, type_categorie__in=[
            CategorieSante.TypeCategorie.SERVICE,
            CategorieSante.TypeCategorie.SPECIALITE,
        ]),
        "q": q,
        "ville": ville,
        "specialite": specialite,
        "urgence": urgence,
        "domicile": domicile,
        "nb_results": pros.distinct().count(),
    })


def detail_professionnel(request, slug):
    pro = get_object_or_404(_pros_actifs().select_related("ville").prefetch_related("specialites"), slug=slug)
    similaires = _pros_actifs().filter(ville=pro.ville).exclude(pk=pro.pk).select_related("ville")[:4]
    return render(request, "sante/detail_professionnel.html", {"pro": pro, "similaires": similaires})


def inscrire_professionnel(request):
    if request.method == "POST":
        form = ProfessionnelSanteForm(request.POST)
        if form.is_valid():
            pro = form.save(commit=False)
            if request.user.is_authenticated:
                pro.auteur = request.user
            pro.is_active = False
            pro.save()
            form.save_m2m()
            messages.success(request, "Profil reçu. Notre équipe le vérifiera avant publication.")
            return redirect("sante:accueil")
        messages.error(request, "Vérifiez les informations du profil.")
    else:
        form = ProfessionnelSanteForm()
    return render(request, "sante/inscrire_professionnel.html", {"form": form})


def demande(request):
    if request.method == "POST":
        form = DemandeSanteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Demande envoyée. Un prestataire santé pourra vous contacter.")
            return redirect("sante:accueil")
        messages.error(request, "Vérifiez les informations de votre demande.")
    else:
        form = DemandeSanteForm()
    demandes = DemandeSante.objects.filter(is_active=True).select_related("ville")[:12]
    return render(request, "sante/demande.html", {"form": form, "demandes": demandes})
