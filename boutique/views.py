"""
boutique/views.py — Vues du module Boutique Digitale E-Shelle
Catalogue produits, détail, panier, checkout, téléchargement.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib import messages
import json

from .models import (
    CategorieProduit, Produit, Panier, LignePanier,
    Commande, LigneCommande, Telechargement
)


def index(request):
    """Page d'accueil de la boutique."""
    produits_featured = Produit.objects.filter(is_published=True, is_featured=True)[:6]
    produits_recents  = Produit.objects.filter(is_published=True).order_by("-created_at")[:12]
    categories        = CategorieProduit.objects.filter(active=True)

    context = {
        "produits_featured": produits_featured,
        "produits_recents":  produits_recents,
        "categories":        categories,
    }
    return render(request, "boutique/index.html", context)


def catalogue(request):
    """Catalogue complet avec filtres."""
    produits   = Produit.objects.filter(is_published=True).select_related("categorie")
    categories = CategorieProduit.objects.filter(active=True)

    # Filtres
    cat_slug   = request.GET.get("categorie", "")
    type_prod  = request.GET.get("type", "")
    recherche  = request.GET.get("q", "")
    gratuit    = request.GET.get("gratuit", "")
    tri        = request.GET.get("tri", "-created_at")

    if cat_slug:
        produits = produits.filter(categorie__slug=cat_slug)
    if type_prod:
        produits = produits.filter(type_produit=type_prod)
    if gratuit:
        produits = produits.filter(is_gratuit=True)
    if recherche:
        produits = produits.filter(
            Q(titre__icontains=recherche) | Q(description__icontains=recherche)
            | Q(titre_en__icontains=recherche) | Q(description_en__icontains=recherche)
        )

    produits = produits.order_by(tri)

    context = {
        "produits":   produits,
        "categories": categories,
        "cat_slug":   cat_slug,
        "recherche":  recherche,
        "types":      Produit.TYPES,
    }
    return render(request, "boutique/catalogue.html", context)


def detail_produit(request, slug):
    """Page détail d'un produit."""
    produit   = get_object_or_404(Produit, slug=slug, is_published=True)
    similaires = Produit.objects.filter(
        categorie=produit.categorie, is_published=True
    ).exclude(pk=produit.pk)[:4]
    avis       = produit.avis.select_related("utilisateur").order_by("-created_at")

    context = {
        "produit":   produit,
        "similaires": similaires,
        "avis":       avis,
    }
    return render(request, "boutique/detail.html", context)


def _get_panier(request):
    """Récupère ou crée le panier de l'utilisateur (connecté ou session)."""
    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(utilisateur=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        panier, _  = Panier.objects.get_or_create(session_key=session_key)
    return panier


def voir_panier(request):
    """Page panier."""
    panier = _get_panier(request)
    context = {"panier": panier}
    return render(request, "boutique/panier.html", context)


@require_POST
def ajouter_au_panier(request, produit_id):
    """Ajoute un produit au panier (AJAX ou form)."""
    produit = get_object_or_404(Produit, pk=produit_id, is_published=True)
    panier  = _get_panier(request)

    ligne, created = LignePanier.objects.get_or_create(panier=panier, produit=produit)
    if not created:
        ligne.quantite += 1
        ligne.save()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        from django.http import JsonResponse
        return JsonResponse({"nb_articles": panier.nb_articles, "total": str(panier.total)})

    product_title = produit.titre_en or produit.titre if request.LANGUAGE_CODE == "en" else produit.titre
    messages.success(request, f'"{product_title}" added to your cart.' if request.LANGUAGE_CODE == "en" else f"« {product_title} » ajouté au panier.")
    return redirect("boutique:panier")


@require_POST
def retirer_du_panier(request, ligne_id):
    """Retire une ligne du panier."""
    panier = _get_panier(request)
    LignePanier.objects.filter(pk=ligne_id, panier=panier).delete()
    return redirect("boutique:panier")


@login_required
def checkout(request):
    """Page de paiement / finalisation commande."""
    panier = _get_panier(request)
    if not panier.lignes.exists():
        messages.warning(request, "Your cart is empty." if request.LANGUAGE_CODE == "en" else "Votre panier est vide.")
        return redirect("boutique:catalogue")

    if request.method == "POST":
        # Créer la commande
        commande = Commande.objects.create(
            utilisateur=request.user,
            montant_total=panier.total,
            email_acheteur=request.user.email,
            telephone=request.POST.get("telephone", ""),
        )
        for ligne in panier.lignes.all():
            LigneCommande.objects.create(
                commande=commande,
                produit=ligne.produit,
                quantite=ligne.quantite,
                prix_unit=ligne.produit.prix,
            )
        # Vider le panier
        panier.lignes.all().delete()
        # Rediriger vers le paiement Mobile Money
        return redirect("payments:initier", commande_id=commande.pk)

    context = {"panier": panier}
    return render(request, "boutique/checkout.html", context)


@login_required
def telecharger(request, token):
    """Téléchargement sécurisé d'un produit digital."""
    telechargement = get_object_or_404(Telechargement, token=token, utilisateur=request.user)

    if not telechargement.est_valide:
        raise Http404("Ce lien de téléchargement est expiré ou invalide.")

    produit = telechargement.produit
    if not produit.fichier:
        raise Http404("Aucun fichier disponible pour ce produit.")

    telechargement.nb_telechargements += 1
    telechargement.save(update_fields=["nb_telechargements"])

    return FileResponse(
        produit.fichier.open("rb"),
        as_attachment=True,
        filename=produit.fichier.name.split("/")[-1]
    )
