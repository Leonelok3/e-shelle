"""
services/views.py — Vues du module Services & Création Web E-Shelle
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import translation
from .models import OffreService, ProjetPortfolio, CategoriePortfolio, Devis, ContactMessage


def index(request):
    """Page d'accueil des services."""
    offres    = OffreService.objects.filter(is_active=True).order_by("ordre")
    projets   = ProjetPortfolio.objects.filter(is_published=True, is_featured=True)[:6]
    with translation.override(request.LANGUAGE_CODE):
        context = {"offres": list(offres), "projets": list(projets)}
    return render(request, "services/index.html", context)


def portfolio(request):
    """Portfolio des projets réalisés."""
    categories = CategoriePortfolio.objects.all()
    projets    = ProjetPortfolio.objects.filter(is_published=True)

    cat_slug = request.GET.get("categorie", "")
    if cat_slug:
        projets = projets.filter(categorie__slug=cat_slug)

    with translation.override(request.LANGUAGE_CODE):
        context = {"projets": list(projets), "categories": list(categories), "cat_slug": cat_slug}
    return render(request, "services/portfolio.html", context)


def configurateur(request):
    """Wizard interactif de configuration de projet et génération de devis."""
    offres = OffreService.objects.filter(is_active=True).order_by("ordre")
    with translation.override(request.LANGUAGE_CODE):
        context = {"offres": list(offres)}
    return render(request, "services/configurateur.html", context)


def contact(request):
    """Formulaire de contact / demande de renseignements."""
    if request.method == "POST":
        msg = ContactMessage(
            nom=request.POST.get("nom", ""),
            email=request.POST.get("email", ""),
            telephone=request.POST.get("telephone", ""),
            sujet=request.POST.get("sujet", "autre"),
            message=request.POST.get("message", ""),
        )
        msg.save()
        messages.success(request, "Your message has been sent! We will reply within 24 hours." if request.LANGUAGE_CODE == "en" else "Votre message a été envoyé ! Nous vous répondrons sous 24h.")
        return redirect("services:contact")

    return render(request, "services/contact.html")


def devis(request):
    """Formulaire de demande de devis rapide."""
    if request.method == "POST":
        project_type = request.POST.get("type_projet", "autre")
        if project_type not in dict(Devis.TYPES_PROJET):
            project_type = "autre"
        d = Devis(
            nom=request.POST.get("nom", ""),
            email=request.POST.get("email", ""),
            telephone=request.POST.get("telephone", ""),
            entreprise=request.POST.get("entreprise", ""),
            type_projet=project_type,
            budget=request.POST.get("budget", "nd") if request.POST.get("budget", "nd") in dict(Devis.BUDGETS) else "nd",
            delai_souhaite=request.POST.get("delai", ""),
            description=request.POST.get("description", ""),
        )
        if request.user.is_authenticated:
            d.utilisateur = request.user
        d.save()
        messages.success(request, "Your quote request has been received! We will reply within 24 hours." if request.LANGUAGE_CODE == "en" else "Votre demande de devis a été reçue ! Réponse sous 24h.")
        return redirect("services:devis")

    return render(request, "services/devis.html")
