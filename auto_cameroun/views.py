"""
views.py — auto_cameroun
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    Vehicule, PhotoVehicule, FavorisVehicule, SignalementVehicule,
    ProfilAuto, StatutVehicule, DemandeSoumissionVehicule,
)
from .forms import (
    VehiculeForm, PhotoVehiculeFormSet, ProfilAutoForm,
    DemandeEssaiForm, DemandeSoumissionForm, SignalementAutoForm, RechercheAutoForm,
)


def _get_or_create_profil(user):
    profil, _ = ProfilAuto.objects.get_or_create(user=user)
    return profil


# ─────────────────────────────────────────────────────────────────
# CATALOGUE
# ─────────────────────────────────────────────────────────────────

def liste_vehicules(request):
    qs = Vehicule.objects.filter(statut=StatutVehicule.PUBLIE).select_related("proprietaire").prefetch_related("photos")
    form = RechercheAutoForm(request.GET or None)

    if form.is_valid():
        d = form.cleaned_data
        if d.get("q"):
            qs = qs.filter(Q(marque__icontains=d["q"]) | Q(modele__icontains=d["q"]) | Q(description__icontains=d["q"]))
        if d.get("type_transaction"):
            qs = qs.filter(type_transaction=d["type_transaction"])
        if d.get("type_carrosserie"):
            qs = qs.filter(type_carrosserie=d["type_carrosserie"])
        if d.get("carburant"):
            qs = qs.filter(carburant=d["carburant"])
        if d.get("boite"):
            qs = qs.filter(boite=d["boite"])
        if d.get("etat"):
            qs = qs.filter(etat=d["etat"])
        if d.get("ville"):
            qs = qs.filter(ville__icontains=d["ville"])
        if d.get("annee_min"):
            qs = qs.filter(annee__gte=d["annee_min"])
        if d.get("annee_max"):
            qs = qs.filter(annee__lte=d["annee_max"])
        if d.get("prix_min"):
            qs = qs.filter(prix__gte=d["prix_min"])
        if d.get("prix_max"):
            qs = qs.filter(prix__lte=d["prix_max"])
        if d.get("km_max"):
            qs = qs.filter(kilometrage__lte=d["km_max"])

    # Tri
    tri = request.GET.get("tri", "-est_mis_en_avant")
    tris_valides = ["-est_mis_en_avant", "-created_at", "prix", "-prix", "annee", "-annee", "-vues"]
    if tri in tris_valides:
        qs = qs.order_by(tri)

    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get("page"))

    coups_de_coeur = Vehicule.objects.filter(statut=StatutVehicule.PUBLIE, est_coup_de_coeur=True)[:4]

    return render(request, "auto_cameroun/liste_vehicules.html", {
        "vehicules": page,
        "form": form,
        "coups_de_coeur": coups_de_coeur,
        "total": paginator.count,
    })


def detail_vehicule(request, slug):
    vehicule = get_object_or_404(Vehicule, slug=slug)

    # Compteur de vues
    if not request.session.get(f"vue_auto_{vehicule.pk}"):
        Vehicule.objects.filter(pk=vehicule.pk).update(vues=vehicule.vues + 1)
        request.session[f"vue_auto_{vehicule.pk}"] = True

    photos = vehicule.photos.all()
    est_favori = False
    if request.user.is_authenticated:
        est_favori = FavorisVehicule.objects.filter(user=request.user, vehicule=vehicule).exists()

    # Formulaire essai
    essai_form = DemandeEssaiForm()
    if request.method == "POST" and vehicule.statut == StatutVehicule.PUBLIE:
        essai_form = DemandeEssaiForm(request.POST)
        if essai_form.is_valid():
            demande = essai_form.save(commit=False)
            demande.vehicule = vehicule
            demande.save()
            messages.success(request, "Votre demande d'essai a été envoyée ! Le vendeur vous contactera.")
            return redirect("auto:detail_vehicule", slug=slug)

    similaires = Vehicule.objects.filter(
        statut=StatutVehicule.PUBLIE,
        type_carrosserie=vehicule.type_carrosserie,
        type_transaction=vehicule.type_transaction,
    ).exclude(pk=vehicule.pk).order_by("-est_mis_en_avant")[:3]

    stats = {}
    if request.user == vehicule.proprietaire or (request.user.is_authenticated and request.user.is_superuser):
        stats = {
            "vues": vehicule.vues,
            "favoris_count": vehicule.favoris.count(),
            "essais_count": vehicule.demandes_essai.count(),
        }

    return render(request, "auto_cameroun/detail_vehicule.html", {
        "vehicule": vehicule,
        "photos": photos,
        "est_favori": est_favori,
        "essai_form": essai_form,
        "similaires": similaires,
        "stats": stats,
    })


# ─────────────────────────────────────────────────────────────────
# ESPACE PUBLIC VENDEUR / GARAGE
# ─────────────────────────────────────────────────────────────────

def espace_vendeur(request, username):
    """Vitrine publique d'un vendeur auto avec ses véhicules en vente/location."""
    User = get_user_model()
    vendeur = get_object_or_404(User, username=username, is_active=True)
    profil, _ = ProfilAuto.objects.get_or_create(user=vendeur)
    vehicules = (
        Vehicule.objects.filter(proprietaire=vendeur, statut=StatutVehicule.PUBLIE)
        .select_related("proprietaire")
        .prefetch_related("photos")
        .order_by("-est_mis_en_avant", "-est_coup_de_coeur", "-date_publication", "-created_at")
    )
    stats = {
        "vehicules": vehicules.count(),
        "ventes": vehicules.filter(type_transaction="VENTE").count(),
        "locations": vehicules.filter(type_transaction="LOCATION").count(),
        "vues": sum(v.vues for v in vehicules),
        "favoris": sum(v.favoris.count() for v in vehicules),
    }
    villes = vehicules.values_list("ville", flat=True).distinct()
    return render(request, "auto_cameroun/espace_vendeur.html", {
        "vendeur": vendeur,
        "profil": profil,
        "vehicules": vehicules,
        "stats": stats,
        "villes": villes,
    })


# ─────────────────────────────────────────────────────────────────
# MON COMPTE
# ─────────────────────────────────────────────────────────────────

@login_required
def mon_compte_auto(request):
    profil = _get_or_create_profil(request.user)
    if request.method == "POST":
        form = ProfilAutoForm(request.POST, request.FILES, instance=profil)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect("auto:mon_compte")
    else:
        form = ProfilAutoForm(instance=profil)
    return render(request, "auto_cameroun/mon_compte/dashboard.html", {"form": form, "profil": profil})


@login_required
def mes_vehicules(request):
    profil = _get_or_create_profil(request.user)
    vehicules = Vehicule.objects.filter(proprietaire=request.user).order_by("-created_at")
    return render(request, "auto_cameroun/mon_compte/mes_vehicules.html", {
        "vehicules": vehicules, "profil": profil
    })


@login_required
def publier_vehicule(request):
    profil = _get_or_create_profil(request.user)
    if not profil.peut_publier:
        messages.warning(request, "Vous avez atteint la limite de 3 annonces gratuites. Passez en Premium !")
        return redirect("auto:upgrade_premium")

    if request.method == "POST":
        form = VehiculeForm(request.POST)
        formset = PhotoVehiculeFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            vehicule = form.save(commit=False)
            vehicule.proprietaire = request.user
            vehicule.statut = StatutVehicule.PUBLIE
            if profil.est_premium:
                vehicule.est_mis_en_avant = True
            vehicule.save()
            formset.instance = vehicule
            formset.save()
            messages.success(request, "🎉 Votre véhicule est en ligne !")
            return redirect("auto:mes_vehicules")
    else:
        form = VehiculeForm()
        formset = PhotoVehiculeFormSet()

    return render(request, "auto_cameroun/mon_compte/publier_vehicule.html", {
        "form": form, "formset": formset, "profil": profil
    })


@login_required
def modifier_vehicule(request, slug):
    vehicule = get_object_or_404(Vehicule, slug=slug, proprietaire=request.user)
    if request.method == "POST":
        form = VehiculeForm(request.POST, instance=vehicule)
        formset = PhotoVehiculeFormSet(request.POST, request.FILES, instance=vehicule)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Annonce mise à jour.")
            return redirect("auto:mes_vehicules")
    else:
        form = VehiculeForm(instance=vehicule)
        formset = PhotoVehiculeFormSet(instance=vehicule)
    return render(request, "auto_cameroun/mon_compte/publier_vehicule.html", {
        "form": form, "formset": formset, "vehicule": vehicule
    })


@login_required
def supprimer_vehicule(request, slug):
    vehicule = get_object_or_404(Vehicule, slug=slug, proprietaire=request.user)
    if request.method == "POST":
        vehicule.delete()
        messages.success(request, "Annonce supprimée.")
    return redirect("auto:mes_vehicules")


@login_required
def mes_favoris_auto(request):
    favoris = FavorisVehicule.objects.filter(user=request.user).select_related("vehicule").order_by("-created_at")
    return render(request, "auto_cameroun/mon_compte/favoris.html", {"favoris": favoris})


@login_required
def upgrade_premium_auto(request):
    return redirect("payments:premium_marketplace", module="auto")


# ─────────────────────────────────────────────────────────────────
# AJAX
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_favori_auto(request, pk):
    vehicule = get_object_or_404(Vehicule, pk=pk)
    favori, created = FavorisVehicule.objects.get_or_create(user=request.user, vehicule=vehicule)
    if not created:
        favori.delete()
        return JsonResponse({"status": "removed"})
    return JsonResponse({"status": "added"})


@require_POST
def marquer_reserve_auto(request, slug):
    vehicule = get_object_or_404(Vehicule, slug=slug)
    if request.user == vehicule.proprietaire or (request.user.is_authenticated and request.user.is_superuser):
        vehicule.statut = StatutVehicule.RESERVE
        vehicule.save(update_fields=["statut"])
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Unauthorized"}, status=403)


# ─────────────────────────────────────────────────────────────────
# SOUMISSION SANS COMPTE
# ─────────────────────────────────────────────────────────────────

def soumettre_vehicule(request):
    if request.method == "POST":
        form = DemandeSoumissionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre véhicule a été soumis ! Notre équipe le publiera sous 24h.")
            return redirect("auto:liste_vehicules")
    else:
        form = DemandeSoumissionForm()
    return render(request, "auto_cameroun/soumettre_vehicule.html", {"form": form})


def signaler_vehicule(request, vehicule_id):
    vehicule = get_object_or_404(Vehicule, pk=vehicule_id)
    if request.method == "POST":
        form = SignalementAutoForm(request.POST)
        if form.is_valid():
            sig = form.save(commit=False)
            sig.vehicule = vehicule
            if request.user.is_authenticated:
                sig.user = request.user
            sig.save()
            messages.success(request, "Signalement envoyé. Merci !")
            return redirect("auto:detail_vehicule", slug=vehicule.slug)
    else:
        form = SignalementAutoForm()
    return render(request, "auto_cameroun/signaler_vehicule.html", {"form": form, "vehicule": vehicule})
