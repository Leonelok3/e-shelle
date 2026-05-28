"""
views.py — immobilier_cameroun
Toutes les vues publiques et privées de la marketplace immobilière
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import (
    Bien, ProfilImmo, FavorisBien,
    DemandeVisite, StatutBien,
)
from .forms import (
    BienForm, PhotoBienFormSet,
    DemandeVisiteForm, DemandeSoumissionBienForm,
    SignalementForm, RechercheForm,
)
from .utils import calculer_stats_bien

BIENS_PAR_PAGE = 12
MAX_BIENS_GRATUIT = getattr(settings, "IMMOBILIER_MAX_BIENS_GRATUIT", 3)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _get_or_create_profil(user):
    profil, _ = ProfilImmo.objects.get_or_create(user=user)
    return profil


def _check_ownership(bien, user):
    """Retourne True si l'utilisateur est propriétaire du bien ou superuser."""
    return bien.proprietaire == user or user.is_superuser


# ─────────────────────────────────────────────────────────────────
# CATALOGUE — LISTE DES BIENS
# ─────────────────────────────────────────────────────────────────

def liste_biens(request):
    """Page principale : catalogue paginé et filtrable."""
    form = RechercheForm(request.GET or None)
    biens_qs = Bien.objects.filter(statut=StatutBien.PUBLIE).select_related(
        "proprietaire"
    ).prefetch_related("photos", "equipements")

    if form.is_valid():
        data = form.cleaned_data

        if data.get("q"):
            q = data["q"]
            biens_qs = biens_qs.filter(
                Q(titre__icontains=q)
                | Q(description__icontains=q)
                | Q(ville__icontains=q)
                | Q(quartier__icontains=q)
            )
        if data.get("type_bien"):
            biens_qs = biens_qs.filter(type_bien=data["type_bien"])
        if data.get("type_transaction"):
            biens_qs = biens_qs.filter(type_transaction=data["type_transaction"])
        if data.get("ville"):
            biens_qs = biens_qs.filter(ville=data["ville"])
        if data.get("prix_min") is not None:
            biens_qs = biens_qs.filter(prix__gte=data["prix_min"])
        if data.get("prix_max") is not None:
            biens_qs = biens_qs.filter(prix__lte=data["prix_max"])
        if data.get("chambres_min") is not None:
            biens_qs = biens_qs.filter(nombre_chambres__gte=data["chambres_min"])

        tri = data.get("tri") or "-date_publication"
        biens_qs = biens_qs.order_by("-est_mis_en_avant", "-est_coup_de_coeur", tri)
    else:
        biens_qs = biens_qs.order_by("-est_mis_en_avant", "-est_coup_de_coeur", "-date_publication")

    # Biens coups de cœur (sidebar / bandeau)
    coups_de_coeur = Bien.objects.filter(
        statut=StatutBien.PUBLIE, est_coup_de_coeur=True
    ).prefetch_related("photos")[:4]

    paginator = Paginator(biens_qs, BIENS_PAR_PAGE)
    page_obj  = paginator.get_page(request.GET.get("page"))

    # IDs des favoris de l'utilisateur connecté
    favoris_ids = set()
    if request.user.is_authenticated:
        favoris_ids = set(
            FavorisBien.objects.filter(user=request.user).values_list("bien_id", flat=True)
        )

    return render(request, "immobilier_cameroun/liste_biens.html", {
        "page_obj":       page_obj,
        "form":           form,
        "coups_de_coeur": coups_de_coeur,
        "favoris_ids":    favoris_ids,
        "nb_resultats":   biens_qs.count(),
    })


# ─────────────────────────────────────────────────────────────────
# DÉTAIL D'UN BIEN
# ─────────────────────────────────────────────────────────────────

def detail_bien(request, slug):
    bien = get_object_or_404(
        Bien.objects.select_related("proprietaire")
        .prefetch_related("photos", "equipements", "demandes_visite"),
        slug=slug,
        statut__in=[StatutBien.PUBLIE, StatutBien.RESERVE, StatutBien.LOUE_VENDU],
    )

    # Incrément de vues (session pour éviter les doubles comptages)
    session_key = f"immo_bien_vu_{bien.pk}"
    if not request.session.get(session_key):
        Bien.objects.filter(pk=bien.pk).update(vues=bien.vues + 1)
        request.session[session_key] = True

    # Formulaire demande de visite
    visite_form = DemandeVisiteForm(request.POST or None)
    if request.method == "POST" and visite_form.is_valid():
        demande = visite_form.save(commit=False)
        demande.bien = bien
        demande.save()
        messages.success(request, "✅ Votre demande de visite a bien été envoyée ! Le propriétaire vous contactera.")
        return redirect("immobilier:detail_bien", slug=slug)

    # Favori actuel
    est_favori = False
    if request.user.is_authenticated:
        est_favori = FavorisBien.objects.filter(user=request.user, bien=bien).exists()

    # Biens similaires
    similaires = Bien.objects.filter(
        statut=StatutBien.PUBLIE,
        type_bien=bien.type_bien,
        ville=bien.ville,
    ).exclude(pk=bien.pk).prefetch_related("photos")[:4]

    return render(request, "immobilier_cameroun/detail_bien.html", {
        "bien":        bien,
        "photos":      bien.photos.all(),
        "equipements": bien.equipements.all(),
        "visite_form": visite_form,
        "est_favori":  est_favori,
        "similaires":  similaires,
        "stats":       calculer_stats_bien(bien),
    })


# ─────────────────────────────────────────────────────────────────
# ESPACE PUBLIC AGENT — LIEN PARTAGEABLE
# ─────────────────────────────────────────────────────────────────

def espace_agent(request, username):
    """Vitrine publique d'un agent/propriétaire avec toutes ses offres publiées."""
    User = get_user_model()
    agent = get_object_or_404(User, username=username, is_active=True)
    profil, _ = ProfilImmo.objects.get_or_create(user=agent)
    biens_qs = (
        Bien.objects.filter(proprietaire=agent, statut=StatutBien.PUBLIE)
        .select_related("proprietaire")
        .prefetch_related("photos", "equipements")
        .order_by("-est_mis_en_avant", "-est_coup_de_coeur", "-date_publication")
    )

    stats = {
        "biens": biens_qs.count(),
        "vues": sum(b.vues for b in biens_qs),
        "favoris": sum(b.nb_favoris for b in biens_qs),
        "locations": biens_qs.filter(type_transaction="LOCATION").count(),
        "ventes": biens_qs.filter(type_transaction="VENTE").count(),
    }

    villes = biens_qs.values_list("ville", flat=True).distinct()
    favoris_ids = set()
    if request.user.is_authenticated:
        favoris_ids = set(
            FavorisBien.objects.filter(user=request.user).values_list("bien_id", flat=True)
        )

    return render(request, "immobilier_cameroun/espace_agent.html", {
        "agent": agent,
        "profil": profil,
        "biens": biens_qs,
        "stats": stats,
        "villes": villes,
        "favoris_ids": favoris_ids,
    })


# ─────────────────────────────────────────────────────────────────
# RECHERCHE
# ─────────────────────────────────────────────────────────────────

def recherche_biens(request):
    """Recherche full-text avec filtres avancés."""
    return liste_biens(request)  # Réutilise liste_biens avec le formulaire


# ─────────────────────────────────────────────────────────────────
# INSCRIPTION / COMPTE
# ─────────────────────────────────────────────────────────────────

def inscription(request):
    """Redirige vers l'inscription générale du projet (accounts)."""
    return redirect("accounts:register")


# ─────────────────────────────────────────────────────────────────
# TABLEAU DE BORD PROPRIÉTAIRE
# ─────────────────────────────────────────────────────────────────

@login_required
def mon_compte(request):
    profil = _get_or_create_profil(request.user)
    mes_biens = Bien.objects.filter(proprietaire=request.user).prefetch_related("photos").order_by("-created_at")
    nouvelles_demandes = DemandeVisite.objects.filter(
        bien__proprietaire=request.user, statut="EN_ATTENTE"
    ).count()

    stats = {
        "biens_publies":  mes_biens.filter(statut=StatutBien.PUBLIE).count(),
        "vues_totales":   sum(b.vues for b in mes_biens),
        "favoris_total":  sum(b.nb_favoris for b in mes_biens),
        "nouvelles_demandes": nouvelles_demandes,
    }

    return render(request, "immobilier_cameroun/mon_compte/dashboard.html", {
        "profil":      profil,
        "mes_biens":   mes_biens[:5],
        "stats":       stats,
    })


# ─────────────────────────────────────────────────────────────────
# MES BIENS
# ─────────────────────────────────────────────────────────────────

@login_required
def mes_biens(request):
    profil = _get_or_create_profil(request.user)
    biens  = Bien.objects.filter(proprietaire=request.user).prefetch_related("photos").order_by("-created_at")
    return render(request, "immobilier_cameroun/mon_compte/mes_biens.html", {
        "profil": profil,
        "biens":  biens,
    })


# ─────────────────────────────────────────────────────────────────
# PUBLIER UN BIEN
# ─────────────────────────────────────────────────────────────────

@login_required
def publier_bien(request):
    profil = _get_or_create_profil(request.user)

    if request.method == "POST":
        form    = BienForm(request.POST, user=request.user)
        formset = PhotoBienFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            bien = form.save(commit=False)
            bien.proprietaire = request.user

            # Statut initial selon le type de compte
            bien.statut           = StatutBien.PUBLIE
            bien.date_publication = timezone.now()
            if profil.est_premium_actif:
                bien.est_mis_en_avant = True

            bien.save()

            # Sauvegarde des équipements (gérée dans le form.save())
            form.save_m2m() if hasattr(form, "save_m2m") else None

            # Photos
            formset.instance = bien
            photos_sauvegardees = formset.save(commit=False)
            for i, photo in enumerate(photos_sauvegardees):
                if i == 0 and not any(p.est_photo_principale for p in photos_sauvegardees):
                    photo.est_photo_principale = True
                photo.ordre = i
                photo.save()
            for deleted in formset.deleted_objects:
                deleted.delete()

            messages.success(request, "🎉 Votre bien est en ligne !")

            return redirect("immobilier:mes_biens")
    else:
        form    = BienForm(user=request.user)
        formset = PhotoBienFormSet()

    return render(request, "immobilier_cameroun/mon_compte/publier_bien.html", {
        "form":    form,
        "formset": formset,
        "profil":  profil,
        "is_create": True,
    })


# ─────────────────────────────────────────────────────────────────
# MODIFIER UN BIEN
# ─────────────────────────────────────────────────────────────────

@login_required
def modifier_bien(request, slug):
    bien = get_object_or_404(Bien, slug=slug)

    if not _check_ownership(bien, request.user):
        return HttpResponseForbidden("Vous n'êtes pas autorisé à modifier ce bien.")

    if request.method == "POST":
        form    = BienForm(request.POST, instance=bien, user=request.user)
        formset = PhotoBienFormSet(request.POST, request.FILES, instance=bien)

        if form.is_valid() and formset.is_valid():
            form.save()
            photos_sauvegardees = formset.save(commit=False)
            for photo in photos_sauvegardees:
                photo.save()
            for deleted in formset.deleted_objects:
                deleted.delete()
            messages.success(request, "✅ Bien modifié avec succès.")
            return redirect("immobilier:mes_biens")
    else:
        form    = BienForm(instance=bien, user=request.user)
        formset = PhotoBienFormSet(instance=bien)

    return render(request, "immobilier_cameroun/mon_compte/modifier_bien.html", {
        "form":    form,
        "formset": formset,
        "bien":    bien,
    })


# ─────────────────────────────────────────────────────────────────
# SUPPRIMER UN BIEN
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def supprimer_bien(request, slug):
    bien = get_object_or_404(Bien, slug=slug)
    if not _check_ownership(bien, request.user):
        return HttpResponseForbidden()
    bien.delete()
    messages.success(request, "🗑️ Bien supprimé.")
    return redirect("immobilier:mes_biens")


# ─────────────────────────────────────────────────────────────────
# FAVORIS
# ─────────────────────────────────────────────────────────────────

@login_required
def mes_favoris(request):
    favoris = FavorisBien.objects.filter(
        user=request.user
    ).select_related("bien").prefetch_related("bien__photos").order_by("-created_at")
    return render(request, "immobilier_cameroun/mon_compte/favoris.html", {
        "favoris": favoris,
    })


# ─────────────────────────────────────────────────────────────────
# UPGRADE PREMIUM
# ─────────────────────────────────────────────────────────────────

@login_required
def upgrade_premium(request):
    return redirect("payments:premium_marketplace", module="immo")


# ─────────────────────────────────────────────────────────────────
# AJAX : TOGGLE FAVORI
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_favori(request, bien_id):
    bien = get_object_or_404(Bien, pk=bien_id, statut=StatutBien.PUBLIE)
    favori, created = FavorisBien.objects.get_or_create(user=request.user, bien=bien)
    if not created:
        favori.delete()
        return JsonResponse({"statut": "retiré", "nb_favoris": bien.nb_favoris})
    return JsonResponse({"statut": "ajouté", "nb_favoris": bien.nb_favoris})


# ─────────────────────────────────────────────────────────────────
# AJAX : MARQUER RÉSERVÉ
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def marquer_reserve(request, slug):
    bien = get_object_or_404(Bien, slug=slug)
    if not _check_ownership(bien, request.user):
        return JsonResponse({"erreur": "Non autorisé"}, status=403)
    bien.statut = StatutBien.RESERVE
    bien.save(update_fields=["statut", "updated_at"])
    return JsonResponse({"statut": "reserve", "label": bien.get_statut_display()})


# ─────────────────────────────────────────────────────────────────
# AJAX : INCRÉMENTER VUE
# ─────────────────────────────────────────────────────────────────

@require_POST
def incrementer_vue(request, bien_id):
    session_key = f"immo_bien_vu_{bien_id}"
    if not request.session.get(session_key):
        Bien.objects.filter(pk=bien_id).update(vues=Q(vues=0) or 1)  # minimal update
        # Méthode plus propre :
        try:
            bien = Bien.objects.get(pk=bien_id)
            bien.vues += 1
            bien.save(update_fields=["vues"])
        except Bien.DoesNotExist:
            pass
        request.session[session_key] = True
    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────
# DEMANDE DE VISITE (page dédiée)
# ─────────────────────────────────────────────────────────────────

def demande_visite(request, slug):
    bien = get_object_or_404(Bien, slug=slug, statut=StatutBien.PUBLIE)
    form = DemandeVisiteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        demande = form.save(commit=False)
        demande.bien = bien
        demande.save()
        messages.success(request, "✅ Demande de visite envoyée avec succès !")
        return redirect("immobilier:detail_bien", slug=slug)
    return render(request, "immobilier_cameroun/demande_visite.html", {
        "bien": bien, "form": form,
    })


# ─────────────────────────────────────────────────────────────────
# SOUMETTRE UN BIEN (workflow public → admin)
# ─────────────────────────────────────────────────────────────────

def soumettre_bien(request):
    form = DemandeSoumissionBienForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "✅ Votre soumission a bien été reçue ! "
            "Notre équipe l'étudiera et vous contactera sous 48h."
        )
        return redirect("immobilier:soumettre_bien")
    return render(request, "immobilier_cameroun/soumettre_bien.html", {"form": form})


# ─────────────────────────────────────────────────────────────────
# SIGNALER UN BIEN
# ─────────────────────────────────────────────────────────────────

def signaler_bien(request, bien_id):
    bien = get_object_or_404(Bien, pk=bien_id)
    form = SignalementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        signalement = form.save(commit=False)
        signalement.bien = bien
        if request.user.is_authenticated:
            signalement.user = request.user
        signalement.save()
        messages.success(request, "📢 Merci, votre signalement a été pris en compte.")
        return redirect("immobilier:detail_bien", slug=bien.slug)
    return render(request, "immobilier_cameroun/signaler_bien.html", {
        "bien": bien, "form": form,
    })
