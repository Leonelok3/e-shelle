"""
payments/views.py — Vues paiement Mobile Money E-Shelle
Initiation paiement, webhook confirmation, historique, packs premium marketplace.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
import json

from .models import Transaction
from boutique.models import Commande
from core.whatsapp import payment_request_url

# ─── Définitions des plans et boosts ─────────────────────────────

PLANS_PREMIUM = {
    "starter": {
        "nom": "Starter", "emoji": "⭐",
        "prix": 2000, "duree_jours": 30,
        "couleur": "#4CAF50", "populaire": False,
        "features": [
            "30 jours Premium",
            "Annonces / biens illimités",
            "Badge Premium visible",
            "Priorité dans les résultats",
        ],
    },
    "pro": {
        "nom": "Pro", "emoji": "🚀",
        "prix": 5000, "duree_jours": 90,
        "couleur": "#4FC3F7", "populaire": True,
        "features": [
            "90 jours Premium",
            "Annonces / biens illimités",
            "Badge Pro + profil mis en avant",
            "Statistiques de base",
            "Support prioritaire",
        ],
    },
    "expert": {
        "nom": "Expert", "emoji": "💎",
        "prix": 15000, "duree_jours": 365,
        "couleur": "#FFD700", "populaire": False,
        "features": [
            "1 an Premium",
            "Tout illimité",
            "Mise en avant permanente sur l'accueil",
            "Statistiques avancées",
            "Badge Expert animé",
            "Support WhatsApp dédié",
        ],
    },
}

BOOSTS_ANNONCE = {
    "REMONTEE_TOP":      {"nom": "Remontée en tête",  "prix": 500,  "duree_jours": 1,  "emoji": "⬆️",  "desc": "Revient en tête de liste pour 24h"},
    "MISE_EN_AVANT_7J":  {"nom": "Mise en avant 7j",  "prix": 1000, "duree_jours": 7,  "emoji": "🌟", "desc": "Encadré doré dans les résultats 7 jours"},
    "MISE_EN_AVANT_30J": {"nom": "Mise en avant 30j", "prix": 3500, "duree_jours": 30, "emoji": "🔥", "desc": "Encadré doré dans les résultats 30 jours"},
    "BADGE_URGENT":      {"nom": "Badge Urgent 7j",   "prix": 800,  "duree_jours": 7,  "emoji": "🔴", "desc": "Badge rouge URGENT visible 7 jours"},
    "PACK_COMPLET":      {"nom": "Pack Complet 30j",  "prix": 5000, "duree_jours": 30, "emoji": "💎", "desc": "Mise en avant + Urgent + Remontée pendant 30 jours"},
}

MODULES_LABEL = {
    "annonces": "Annonces Cam",
    "immo":     "Immobilier",
    "auto":     "Auto Cameroun",
    "agro":     "E-Shelle Agro",
}

MODULES_ICON = {
    "annonces": "📋",
    "immo":     "🏠",
    "auto":     "🚗",
    "agro":     "🌿",
}


def _activer_premium_module(user, module, plan_slug):
    """Active le compte premium sur le bon profil selon le module."""
    from datetime import timedelta
    duree = PLANS_PREMIUM[plan_slug]["duree_jours"]
    expiry = timezone.now().date() + timedelta(days=duree)

    if module == "annonces":
        from annonces_cam.models import ProfilVendeur, TypeCompteVendeur
        profil, _ = ProfilVendeur.objects.get_or_create(user=user)
        if profil.est_premium and profil.date_expiration_premium:
            expiry = profil.date_expiration_premium + timedelta(days=duree)
        profil.compte_type = TypeCompteVendeur.PREMIUM
        profil.date_expiration_premium = expiry
        profil.save(update_fields=["compte_type", "date_expiration_premium"])

    elif module == "immo":
        from immobilier_cameroun.models import ProfilImmo, TypeCompte
        profil, _ = ProfilImmo.objects.get_or_create(user=user)
        if profil.est_premium_actif and profil.date_expiration_premium:
            expiry = profil.date_expiration_premium + timedelta(days=duree)
        profil.compte_type = TypeCompte.PREMIUM
        profil.date_expiration_premium = expiry
        profil.save(update_fields=["compte_type", "date_expiration_premium"])

    elif module == "auto":
        from auto_cameroun.models import ProfilAuto, TypeCompteAuto
        profil, _ = ProfilAuto.objects.get_or_create(user=user)
        if profil.est_premium and profil.date_expiration_premium:
            expiry = profil.date_expiration_premium + timedelta(days=duree)
        profil.compte_type = TypeCompteAuto.PREMIUM
        profil.date_expiration_premium = expiry
        profil.save(update_fields=["compte_type", "date_expiration_premium"])

    elif module == "agro":
        from agro.models import ActeurAgro
        agro_map = {"starter": "silver", "pro": "gold", "expert": "platinum"}
        try:
            acteur = ActeurAgro.objects.get(user=user)
            acteur.plan_premium = agro_map.get(plan_slug, "silver")
            acteur.plan_expiry = expiry
            acteur.est_premium = True
            acteur.save(update_fields=["plan_premium", "plan_expiry", "est_premium"])
        except ActeurAgro.DoesNotExist:
            pass


@login_required
def initier(request, commande_id):
    """Page d'initiation du paiement Mobile Money."""
    commande = get_object_or_404(Commande, pk=commande_id, utilisateur=request.user)
    
    # Construire la liste des articles commandés
    articles = []
    for ligne in commande.lignes.select_related('produit').all():
        articles.append(f"- {ligne.produit.titre} ({ligne.prix_unit|floatformat:0} FCFA)")
    articles_str = "\n".join(articles)
    
    message = (
        f"Bonjour E-Shelle 👋,\n\n"
        f"Je souhaite régler ma commande sur la Boutique Digitale :\n\n"
        f"Référence de commande : {commande.reference}\n"
        f"Articles :\n{articles_str}\n"
        f"Montant total : {commande.montant_total|floatformat:0} FCFA\n\n"
        f"Client : {request.user.get_full_name() or request.user.username} ({request.user.email})\n"
        f"Téléphone : {commande.telephone or 'Non renseigné'}\n\n"
        f"Merci de m'envoyer les instructions de paiement et mon code d'accès après réception du paiement 🙏"
    )
    
    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message)
    
    messages.success(request, "Redirection vers WhatsApp pour finaliser votre commande...")
    return redirect(whatsapp_payment_url)


@login_required
def confirmation(request, tx_id):
    """Page de confirmation après paiement."""
    tx = get_object_or_404(Transaction, pk=tx_id, utilisateur=request.user)
    from boutique.models import Telechargement
    telechargements = Telechargement.objects.filter(
        commande=tx.commande
    ) if tx.commande else []

    return render(request, "payments/confirmation.html", {
        "transaction": tx,
        "telechargements": telechargements,
    })


@login_required
def historique(request):
    """Historique des transactions de l'utilisateur."""
    transactions = Transaction.objects.filter(
        utilisateur=request.user
    ).order_by("-created_at")
    return render(request, "payments/historique.html", {"transactions": transactions})


@csrf_exempt
def webhook(request):
    """Webhook pour les confirmations de paiement Mobile Money (MTN / Airtel)."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        ref  = data.get("reference", "")
        tx   = Transaction.objects.filter(ref_operateur=ref).first()

        if tx:
            statut = data.get("status", "")
            if statut in ("SUCCESS", "SUCCESSFUL"):
                tx.statut = "succes"
            elif statut in ("FAILED", "CANCELLED"):
                tx.statut = "echec"
            tx.save(update_fields=["statut"])

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"ok": True})


@login_required
def payer_formation(request, formation_id):
    """Paiement d'une formation payante via Mobile Money."""
    from formations.models import Formation, Inscription

    formation = get_object_or_404(Formation, pk=formation_id, is_published=True)

    # Déjà inscrit ?
    if Inscription.objects.filter(utilisateur=request.user, formation=formation).exists():
        messages.info(request, "Vous êtes déjà inscrit à cette formation.")
        return redirect("formations:detail", slug=formation.slug)

    message = (
        f"Bonjour E-Shelle 👋,\n\n"
        f"Je souhaite m'inscrire à la formation suivante :\n\n"
        f"Formation : {formation.titre}\n"
        f"Prix : {formation.prix|floatformat:0} FCFA\n\n"
        f"Client : {request.user.get_full_name() or request.user.username} ({request.user.email})\n\n"
        f"Merci de m'envoyer les instructions de paiement et mon lien d'accès à la formation après réception du paiement 🙏"
    )

    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message)

    messages.success(request, "Redirection vers WhatsApp pour finaliser votre inscription...")
    return redirect(whatsapp_payment_url)


# ─── PACKS PREMIUM MARKETPLACE ───────────────────────────────────

def _get_plans_for_module(module):
    """Charge les plans depuis la DB. Fallback sur les plans hardcodés si la DB est vide."""
    from .models import PlanPremiumApp
    qs = PlanPremiumApp.objects.filter(module=module, actif=True).order_by("ordre", "prix")
    if qs.exists():
        return {p.slug: p.to_dict() for p in qs}
    return PLANS_PREMIUM


@login_required
def premium_marketplace(request, module):
    """Page de choix du pack premium pour un module marketplace."""
    all_modules = dict(
        list(MODULES_LABEL.items()) +
        [("gaz", "E-Shelle Gaz"), ("pharma", "E-Shelle Pharma"),
         ("pressing", "E-Shelle Pressing"), ("formations", "Formations"),
         ("boutique", "Boutique"), ("rencontres", "E-Shelle Love"),
         ("njangi", "Njangi")]
    )
    all_icons = dict(
        list(MODULES_ICON.items()) +
        [("gaz", "🔥"), ("pharma", "💊"), ("pressing", "👔"),
         ("formations", "📚"), ("boutique", "🛒"), ("rencontres", "❤️"), ("njangi", "💰")]
    )
    if module not in all_modules:
        messages.error(request, "Module invalide.")
        return redirect("home")
    plans = _get_plans_for_module(module)
    for slug, plan in plans.items():
        plan["whatsapp_url"] = payment_request_url(
            service=f"{all_modules[module]} - Pack {plan['nom']}",
            amount=f"{plan['prix']} FCFA",
            user=request.user,
            details=f"Module {module}, plan {slug}, duree {plan['duree_jours']} jours",
        )
    return render(request, "payments/premium_marketplace.html", {
        "module":       module,
        "module_label": all_modules[module],
        "module_icon":  all_icons.get(module, "⭐"),
        "plans":        plans,
    })


@login_required
def payer_premium(request, module, plan_slug):
    """Redirige les demandes premium vers WhatsApp pour validation manuelle."""
    plans = _get_plans_for_module(module)
    if plan_slug not in plans:
        messages.error(request, "Paramètres invalides.")
        return redirect("home")

    plan = plans[plan_slug]
    module_label = MODULES_LABEL.get(module, module)
    
    message = (
        f"Bonjour E-Shelle 👋,\n\n"
        f"Je souhaite activer le Pack Premium suivant :\n\n"
        f"Module : {module_label}\n"
        f"Pack : {plan['nom']} ({plan['duree_jours']} jours)\n"
        f"Prix : {plan['prix']} FCFA\n\n"
        f"Client : {request.user.get_full_name() or request.user.username} ({request.user.email})\n\n"
        f"Merci de valider mon accès Premium après réception du paiement 🙏"
    )

    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message)

    messages.success(request, "Redirection vers WhatsApp pour finaliser votre abonnement Premium...")
    return redirect(whatsapp_payment_url)


@login_required
def confirmation_premium(request, tx_id):
    """Confirmation après achat d'un pack premium."""
    tx = get_object_or_404(Transaction, pk=tx_id, utilisateur=request.user)
    module = (tx.metadata or {}).get("module", "")
    retour_urls = {
        "annonces": "/annonces/compte/mes-annonces/",
        "immo":     "/immobilier/compte/mes-biens/",
        "auto":     "/auto/compte/mes-vehicules/",
        "agro":     "/agro/dashboard/",
    }
    return render(request, "payments/confirmation_premium.html", {
        "transaction":  tx,
        "module":       module,
        "module_label": MODULES_LABEL.get(module, ""),
        "module_icon":  MODULES_ICON.get(module, ""),
        "retour_url":   retour_urls.get(module, "/"),
    })


@login_required
def booster_annonce(request, annonce_id, type_boost):
    """Paiement pour booster une annonce individuelle."""
    from annonces_cam.models import Annonce, BoostAnnonce
    from datetime import timedelta

    annonce = get_object_or_404(Annonce, pk=annonce_id, vendeur=request.user)

    if type_boost not in BOOSTS_ANNONCE:
        messages.error(request, "Type de boost invalide.")
        return redirect("annonces:mes_annonces")

    boost_info = BOOSTS_ANNONCE[type_boost]
    
    message = (
        f"Bonjour E-Shelle 👋,\n\n"
        f"Je souhaite booster mon annonce suivante :\n\n"
        f"Annonce : {annonce.titre} (ID #{annonce.pk})\n"
        f"Option de boost : {boost_info['nom']}\n"
        f"Prix : {boost_info['prix']} FCFA\n\n"
        f"Vendeur : {request.user.get_full_name() or request.user.username} ({request.user.email})\n\n"
        f"Merci d'activer le boost après réception du paiement 🙏"
    )

    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message)

    messages.success(request, "Redirection vers WhatsApp pour finaliser le boost de votre annonce...")
    return redirect(whatsapp_payment_url)
