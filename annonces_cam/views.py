"""
views.py — annonces_cam
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from .models import (
    Annonce, PhotoAnnonce, FavoriAnnonce, SignalementAnnonce,
    ProfilVendeur, Categorie, StatutAnnonce,
    ConversationAnnonce, MessageAnnonce,
)
from .forms import (
    AnnonceForm, PhotoAnnonceFormSet, ProfilVendeurForm,
    SignalementAnnonceForm, RechercheAnnonceForm, MessageAnnonceForm,
)


def _get_or_create_profil(user):
    profil, _ = ProfilVendeur.objects.get_or_create(user=user)
    return profil


# ─────────────────────────────────────────────────────────────────
# CATALOGUE
# ─────────────────────────────────────────────────────────────────

def liste_annonces(request):
    qs = Annonce.objects.publiees().select_related("vendeur", "categorie").prefetch_related("photos")

    form = RechercheAnnonceForm(request.GET or None)
    if form.is_valid():
        d = form.cleaned_data
        if d.get("q"):
            qs = qs.filter(
                Q(titre__icontains=d["q"])
                | Q(description__icontains=d["q"])
                | Q(quartier__icontains=d["q"])
            )
        if d.get("categorie"):
            from .models import Categorie as Cat
            try:
                cat = Cat.objects.get(pk=d["categorie"])
                sous_ids = list(cat.sous_categories.values_list("pk", flat=True))
                ids = [cat.pk] + sous_ids
                qs = qs.filter(categorie__in=ids)
            except Cat.DoesNotExist:
                pass
        if d.get("ville"):
            qs = qs.filter(ville__iexact=d["ville"])
        if d.get("etat"):
            qs = qs.filter(etat_produit=d["etat"])
        if d.get("prix_min"):
            qs = qs.filter(prix__gte=d["prix_min"])
        if d.get("prix_max"):
            qs = qs.filter(prix__lte=d["prix_max"])

    # Tri
    tri = request.GET.get("tri", "-est_mise_en_avant")
    tris_valides = ["-est_mise_en_avant", "-date_publication", "prix", "-prix", "-vues"]
    if tri in tris_valides:
        qs = qs.order_by(tri)

    paginator = Paginator(qs, 16)
    page = paginator.get_page(request.GET.get("page"))

    categories = Categorie.objects.filter(parent__isnull=True, est_active=True).prefetch_related("sous_categories").order_by("ordre", "nom")
    coups_de_coeur = Annonce.objects.coups_de_coeur()[:6]
    urgentes = Annonce.objects.urgentes()[:4]

    return render(request, "annonces_cam/liste_annonces.html", {
        "annonces":       page,
        "form":           form,
        "categories":     categories,
        "coups_de_coeur": coups_de_coeur,
        "urgentes":       urgentes,
        "total":          paginator.count,
    })


def annonces_par_categorie(request, slug_categorie):
    categorie = get_object_or_404(Categorie, slug=slug_categorie, est_active=True)
    sous_ids  = list(categorie.sous_categories.values_list("pk", flat=True))
    ids       = [categorie.pk] + sous_ids
    qs = Annonce.objects.publiees().filter(categorie__in=ids).select_related("vendeur", "categorie").prefetch_related("photos")

    tri = request.GET.get("tri", "-est_mise_en_avant")
    tris_valides = ["-est_mise_en_avant", "-date_publication", "prix", "-prix", "-vues"]
    if tri in tris_valides:
        qs = qs.order_by(tri)

    paginator = Paginator(qs, 16)
    page      = paginator.get_page(request.GET.get("page"))

    return render(request, "annonces_cam/annonces_par_categorie.html", {
        "categorie":  categorie,
        "annonces":   page,
        "total":      paginator.count,
    })


def detail_annonce(request, slug):
    annonce = get_object_or_404(Annonce, slug=slug)

    # Compteur de vues
    if not request.session.get(f"vue_ann_{annonce.pk}"):
        Annonce.objects.filter(pk=annonce.pk).update(vues=annonce.vues + 1)
        request.session[f"vue_ann_{annonce.pk}"] = True

    photos     = annonce.photos.all()
    est_favori = False
    if request.user.is_authenticated:
        est_favori = FavoriAnnonce.objects.filter(user=request.user, annonce=annonce).exists()

    # Formulaire message (messagerie interne)
    msg_form = MessageAnnonceForm()
    if request.method == "POST" and request.user.is_authenticated and annonce.statut == StatutAnnonce.PUBLIEE:
        msg_form = MessageAnnonceForm(request.POST)
        if msg_form.is_valid():
            conv, _ = ConversationAnnonce.objects.get_or_create(
                annonce=annonce,
                acheteur=request.user,
                vendeur=annonce.vendeur,
            )
            MessageAnnonce.objects.create(
                conversation=conv,
                expediteur=request.user,
                destinataire=annonce.vendeur,
                contenu=msg_form.cleaned_data["contenu"],
            )
            Annonce.objects.filter(pk=annonce.pk).update(nombre_contacts=annonce.nombre_contacts + 1)
            messages.success(request, "Message envoyé au vendeur !")
            return redirect("annonces:detail_annonce", slug=slug)

    similaires = Annonce.objects.publiees().filter(
        categorie=annonce.categorie,
    ).exclude(pk=annonce.pk).order_by("-est_mise_en_avant")[:4]

    stats = {}
    if request.user.is_authenticated and (request.user == annonce.vendeur or request.user.is_superuser):
        stats = {
            "vues":      annonce.vues,
            "contacts":  annonce.nombre_contacts,
            "favoris":   annonce.nombre_favoris,
        }

    return render(request, "annonces_cam/detail_annonce.html", {
        "annonce":    annonce,
        "photos":     photos,
        "est_favori": est_favori,
        "msg_form":   msg_form,
        "similaires": similaires,
        "stats":      stats,
    })


# ─────────────────────────────────────────────────────────────────
# MON COMPTE
# ─────────────────────────────────────────────────────────────────

@login_required
def mon_compte_annonces(request):
    profil = _get_or_create_profil(request.user)
    if request.method == "POST":
        form = ProfilVendeurForm(request.POST, request.FILES, instance=profil)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect("annonces:mon_compte")
    else:
        form = ProfilVendeurForm(instance=profil)
    stats = {
        "total":     Annonce.objects.filter(vendeur=request.user).count(),
        "publiees":  Annonce.objects.filter(vendeur=request.user, statut=StatutAnnonce.PUBLIEE).count(),
        "en_attente": Annonce.objects.filter(vendeur=request.user, statut=StatutAnnonce.EN_ATTENTE_VALIDATION).count(),
        "vendues":   Annonce.objects.filter(vendeur=request.user, statut=StatutAnnonce.VENDUE).count(),
    }
    return render(request, "annonces_cam/mon_compte/dashboard.html", {
        "form": form, "profil": profil, "stats": stats,
    })


@login_required
def mes_annonces(request):
    profil   = _get_or_create_profil(request.user)
    annonces = Annonce.objects.filter(vendeur=request.user).order_by("-created_at")
    return render(request, "annonces_cam/mon_compte/mes_annonces.html", {
        "annonces": annonces, "profil": profil,
    })


@login_required
def publier_annonce(request):
    profil = _get_or_create_profil(request.user)
    if not profil.peut_publier:
        messages.warning(request, "Vous avez atteint la limite de 5 annonces gratuites. Passez en Premium !")
        return redirect("annonces:upgrade_premium")

    if request.method == "POST":
        form    = AnnonceForm(request.POST)
        formset = PhotoAnnonceFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            annonce         = form.save(commit=False)
            annonce.vendeur = request.user
            annonce.statut  = StatutAnnonce.PUBLIEE
            if profil.est_premium:
                annonce.est_mise_en_avant = True
            annonce.save()
            formset.instance = annonce
            formset.save()
            messages.success(request, "🎉 Votre annonce est en ligne !")
            return redirect("annonces:mes_annonces")
    else:
        form    = AnnonceForm()
        formset = PhotoAnnonceFormSet()

    return render(request, "annonces_cam/mon_compte/publier_annonce.html", {
        "form": form, "formset": formset, "profil": profil,
    })


@login_required
def modifier_annonce(request, slug):
    annonce = get_object_or_404(Annonce, slug=slug, vendeur=request.user)
    if request.method == "POST":
        form    = AnnonceForm(request.POST, instance=annonce)
        formset = PhotoAnnonceFormSet(request.POST, request.FILES, instance=annonce)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Annonce mise à jour.")
            return redirect("annonces:mes_annonces")
    else:
        form    = AnnonceForm(instance=annonce)
        formset = PhotoAnnonceFormSet(instance=annonce)
    return render(request, "annonces_cam/mon_compte/publier_annonce.html", {
        "form": form, "formset": formset, "annonce": annonce,
    })


@login_required
def supprimer_annonce(request, slug):
    annonce = get_object_or_404(Annonce, slug=slug, vendeur=request.user)
    if request.method == "POST":
        annonce.delete()
        messages.success(request, "Annonce supprimée.")
    return redirect("annonces:mes_annonces")


@login_required
def marquer_vendue(request, slug):
    annonce = get_object_or_404(Annonce, slug=slug, vendeur=request.user)
    if request.method == "POST":
        annonce.statut = StatutAnnonce.VENDUE
        annonce.save(update_fields=["statut"])
        messages.success(request, "Annonce marquée comme vendue.")
    return redirect("annonces:mes_annonces")


@login_required
def mes_favoris(request):
    favoris = FavoriAnnonce.objects.filter(user=request.user).select_related("annonce__categorie").order_by("-created_at")
    return render(request, "annonces_cam/mon_compte/favoris.html", {"favoris": favoris})


@login_required
def mes_messages(request):
    conversations_acheteur = ConversationAnnonce.objects.filter(acheteur=request.user).select_related("annonce", "vendeur").order_by("-derniere_activite")
    conversations_vendeur  = ConversationAnnonce.objects.filter(vendeur=request.user).select_related("annonce", "acheteur").order_by("-derniere_activite")
    return render(request, "annonces_cam/mon_compte/messages.html", {
        "conversations_acheteur": conversations_acheteur,
        "conversations_vendeur":  conversations_vendeur,
    })


@login_required
def detail_conversation(request, conv_id):
    conv = get_object_or_404(
        ConversationAnnonce,
        pk=conv_id
    )
    if request.user not in [conv.acheteur, conv.vendeur]:
        messages.error(request, "Accès refusé.")
        return redirect("annonces:mes_messages")

    # Marquer les messages reçus comme lus
    conv.messages.filter(lu=False).exclude(expediteur=request.user).update(lu=True)

    if request.method == "POST":
        form = MessageAnnonceForm(request.POST)
        if form.is_valid():
            destinataire = conv.vendeur if request.user == conv.acheteur else conv.acheteur
            MessageAnnonce.objects.create(
                conversation=conv,
                expediteur=request.user,
                destinataire=destinataire,
                contenu=form.cleaned_data["contenu"],
            )
            return redirect("annonces:conversation", conv_id=conv_id)
    else:
        form = MessageAnnonceForm()

    return render(request, "annonces_cam/mon_compte/conversation.html", {
        "conv": conv,
        "messages_list": conv.messages.all(),
        "form": form,
    })


@login_required
def upgrade_premium(request):
    return redirect("payments:premium_marketplace", module="annonces")


# ─────────────────────────────────────────────────────────────────
# AJAX
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_favori(request, pk):
    annonce = get_object_or_404(Annonce, pk=pk)
    favori, created = FavoriAnnonce.objects.get_or_create(user=request.user, annonce=annonce)
    if not created:
        favori.delete()
        Annonce.objects.filter(pk=pk).update(nombre_favoris=max(0, annonce.nombre_favoris - 1))
        return JsonResponse({"status": "removed"})
    Annonce.objects.filter(pk=pk).update(nombre_favoris=annonce.nombre_favoris + 1)
    return JsonResponse({"status": "added"})


@require_POST
def marquer_vendue_ajax(request, slug):
    annonce = get_object_or_404(Annonce, slug=slug)
    if request.user == annonce.vendeur or (request.user.is_authenticated and request.user.is_superuser):
        annonce.statut = StatutAnnonce.VENDUE
        annonce.save(update_fields=["statut"])
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Unauthorized"}, status=403)


# ─────────────────────────────────────────────────────────────────
# SIGNALEMENT
# ─────────────────────────────────────────────────────────────────

def signaler_annonce(request, annonce_id):
    annonce = get_object_or_404(Annonce, pk=annonce_id)
    if request.method == "POST":
        form = SignalementAnnonceForm(request.POST)
        if form.is_valid():
            sig = form.save(commit=False)
            sig.annonce = annonce
            if request.user.is_authenticated:
                sig.user = request.user
            sig.save()
            messages.success(request, "Signalement envoyé. Merci !")
            return redirect("annonces:detail_annonce", slug=annonce.slug)
    else:
        form = SignalementAnnonceForm()
    return render(request, "annonces_cam/signaler_annonce.html", {"form": form, "annonce": annonce})


# ─────────────────────────────────────────────────────────────────
# PROFIL PUBLIC
# ─────────────────────────────────────────────────────────────────

def profil_vendeur_public(request, user_id):
    User  = get_user_model()
    user  = get_object_or_404(User, pk=user_id)
    return _render_profil_vendeur_public(request, user)


def profil_vendeur_username(request, username):
    User = get_user_model()
    user = get_object_or_404(User, username=username, is_active=True)
    return _render_profil_vendeur_public(request, user)


def _render_profil_vendeur_public(request, user):
    try:
        profil = user.profil_vendeur
    except ProfilVendeur.DoesNotExist:
        profil = None
    annonces = Annonce.objects.publiees().filter(vendeur=user).order_by("-est_mise_en_avant", "-date_publication")[:24]
    stats = {
        "annonces": annonces.count(),
        "vues": sum(a.vues for a in annonces),
        "contacts": sum(a.nombre_contacts for a in annonces),
        "favoris": sum(a.nombre_favoris for a in annonces),
    }
    return render(request, "annonces_cam/profil_vendeur.html", {
        "vendeur":  user,
        "profil":   profil,
        "annonces": annonces,
        "stats": stats,
    })
