"""
payments/views.py — Vues paiement Mobile Money E-Shelle
Initiation paiement, webhook confirmation, historique, packs premium marketplace.
"""
import json
import logging
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.core import signing
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import Transaction
from .campay import CampayClient, CampayError, reconcile_transaction
from boutique.models import Commande
from core.whatsapp import payment_request_url

logger = logging.getLogger(__name__)

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
    """Offer CamPay checkout while preserving the existing WhatsApp option."""
    commande = get_object_or_404(Commande, pk=commande_id, utilisateur=request.user)
    
    # Construire la liste des articles commandés
    articles = []
    for ligne in commande.lignes.select_related(
        "produit", "business_catalog_item"
    ).all():
        if ligne.produit_id:
            item_name = ligne.produit.titre
        elif ligne.business_catalog_item_id:
            item_name = ligne.business_catalog_item.title
        else:
            item_name = "Article"
        articles.append(f"- {item_name} ({ligne.prix_unit:.0f} FCFA)")
    articles_str = "\n".join(articles)
    
    message = (
        f"Bonjour {getattr(request, 'site_brand', 'E-Shelle')} 👋,\n\n"
        f"Je souhaite régler ma commande sur la Boutique Digitale :\n\n"
        f"Référence de commande : {commande.reference}\n"
        f"Articles :\n{articles_str}\n"
        f"Montant total : {commande.montant_total:.0f} FCFA\n\n"
        f"Client : {request.user.get_full_name() or request.user.username} ({request.user.email})\n"
        f"Téléphone : {commande.telephone or 'Non renseigné'}\n\n"
        f"Merci de m'envoyer les instructions de paiement et mon code d'accès après réception du paiement 🙏"
    )
    
    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message, number="237693649944" if getattr(request, "is_immigration97", False) else None)
    return _render_payment_choice(
        request,
        title=f"Commande {commande.reference}",
        amount=commande.montant_total,
        campay_url=reverse("payments:campay_order", kwargs={"commande_id": commande.pk}),
        whatsapp_payment_url=whatsapp_payment_url,
    )


def _render_payment_choice(request, *, title, amount, campay_url, whatsapp_payment_url):
    return render(request, "payments/method_choice.html", {
        "title": title,
        "amount": amount,
        "campay_url": campay_url,
        "whatsapp_payment_url": whatsapp_payment_url,
    })


def _campay_return_url(transaction_obj):
    return_token = signing.dumps(
        {"transaction_id": transaction_obj.pk},
        salt="payments.campay.return",
    )
    return f"{reverse('payments:campay_return')}?{urlencode({'token': return_token})}"


def _reuse_existing_campay_checkout(request, fallback_url, *, amount, **lookup):
    transactions = Transaction.objects.filter(methode="campay", **lookup).order_by("-created_at")
    confirmed = transactions.filter(
        statut__in=("pending_awaiting_manual_validation", "succes")
    ).first()
    if confirmed:
        messages.info(request, "Un paiement est déjà confirmé. Veuillez attendre la validation manuelle.")
        return redirect(_campay_return_url(confirmed))

    pending = transactions.filter(statut="en_attente").first()
    if pending:
        if pending.montant == amount and pending.payment_link:
            return redirect(pending.payment_link)
        messages.error(request, "Un paiement est déjà en cours. Contactez-nous sur WhatsApp avant d’en créer un autre.")
        return redirect(fallback_url)
    return None


def _start_campay_checkout(request, transaction_obj, *, description, fallback_url):
    configured_base = getattr(settings, "CAMPAY_PUBLIC_BASE_URL", "")
    if (transaction_obj.metadata or {}).get("immigration97_app_key") == "prep":
        base_url = "https://immigration97.com"
    elif configured_base:
        base_url = configured_base
    elif request.is_secure():
        base_url = request.build_absolute_uri("/").rstrip("/")
    else:
        base_url = ""

    parsed_base = urlparse(base_url)
    if parsed_base.scheme != "https" or not parsed_base.netloc:
        transaction_obj.statut = "echec"
        transaction_obj.erreur = "A public HTTPS return URL is required for CamPay."
        transaction_obj.save(update_fields=["statut", "erreur", "updated_at"])
        _set_app_plan_payment_status(transaction_obj, "failed")
        messages.error(request, "Le paiement en ligne est temporairement indisponible. Vous pouvez continuer sur WhatsApp.")
        return redirect(fallback_url)

    return_url = f"{base_url}{_campay_return_url(transaction_obj)}"
    try:
        client = CampayClient()
        link, provider_reference = client.create_payment_link(
            transaction_obj,
            description=description,
            redirect_url=return_url,
        )
    except CampayError as exc:
        transaction_obj.statut = "echec"
        transaction_obj.erreur = "CamPay checkout could not be started."
        transaction_obj.save(update_fields=["statut", "erreur", "updated_at"])
        _set_app_plan_payment_status(transaction_obj, "failed")
        logger.warning(
            "CamPay checkout failed for transaction %s: %s",
            transaction_obj.reference,
            exc,
        )
        messages.error(request, "CamPay n’a pas pu démarrer le paiement. Vous pouvez réessayer ou continuer sur WhatsApp.")
        return redirect(fallback_url)

    metadata = dict(transaction_obj.metadata or {})
    metadata["campay"] = {
        "mode": client.mode,
        "external_reference": transaction_obj.reference,
    }
    transaction_obj.ref_operateur = provider_reference
    transaction_obj.ref_interne = transaction_obj.reference
    transaction_obj.payment_link = link
    transaction_obj.statut = "en_attente"
    transaction_obj.metadata = metadata
    transaction_obj.erreur = ""
    transaction_obj.save(update_fields=[
        "ref_operateur", "ref_interne", "payment_link", "statut",
        "metadata", "erreur", "updated_at",
    ])
    return redirect(link)


@login_required
@require_POST
def payer_commande_campay(request, commande_id):
    fallback_url = reverse("payments:initier", kwargs={"commande_id": commande_id})
    with db_transaction.atomic():
        commande = get_object_or_404(
            Commande.objects.select_for_update(),
            pk=commande_id,
            utilisateur=request.user,
        )
        if commande.statut != "en_attente" or commande.montant_total <= 0:
            messages.error(request, "Cette commande ne peut pas être payée en ligne.")
            return redirect(fallback_url)
        existing_checkout = _reuse_existing_campay_checkout(
            request,
            fallback_url,
            amount=commande.montant_total,
            commande=commande,
        )
        if existing_checkout:
            return existing_checkout

        tx = Transaction.objects.create(
            utilisateur=request.user,
            commande=commande,
            type_tx="achat_produit",
            methode="campay",
            montant=commande.montant_total,
            devise="XAF",
            statut="initie",
        )
    return _start_campay_checkout(
        request,
        tx,
        description=f"E-Shelle commande {commande.reference}",
        fallback_url=fallback_url,
    )


@login_required
@require_POST
def payer_formation_campay(request, formation_id):
    from formations.models import Formation, Inscription

    fallback_url = reverse("payments:payer_formation", kwargs={"formation_id": formation_id})
    with db_transaction.atomic():
        formation = get_object_or_404(
            Formation.objects.select_for_update(),
            pk=formation_id,
            is_published=True,
        )
        if formation.prix <= 0 or Inscription.objects.filter(
            utilisateur=request.user, formation=formation
        ).exists():
            messages.error(request, "Cette formation ne nécessite pas de paiement ou vous y êtes déjà inscrit.")
            return redirect(fallback_url)
        existing_checkout = _reuse_existing_campay_checkout(
            request,
            fallback_url,
            amount=formation.prix,
            utilisateur=request.user,
            formation=formation,
        )
        if existing_checkout:
            return existing_checkout

        tx = Transaction.objects.create(
            utilisateur=request.user,
            formation=formation,
            type_tx="achat_cours",
            methode="campay",
            montant=formation.prix,
            devise="XAF",
            statut="initie",
        )
    return _start_campay_checkout(
        request,
        tx,
        description=f"E-Shelle formation {formation.pk}",
        fallback_url=fallback_url,
    )


@login_required
@require_POST
def payer_immigration_plan_campay(request, plan_id):
    from accounts.models import AppPlan, AppSubscription, PaymentHistory

    fallback_url = reverse("accounts:upgrade") + "?app=prep"
    with db_transaction.atomic():
        plan = get_object_or_404(
            AppPlan.objects.select_for_update(),
            pk=plan_id,
            app_key="prep",
            is_active=True,
            is_free=False,
        )
        if plan.price_xaf <= 0:
            messages.error(request, "Ce plan ne peut pas être payé en ligne.")
            return redirect(fallback_url)

        existing_checkout = _reuse_existing_campay_checkout(
            request,
            fallback_url,
            amount=plan.price_xaf,
            utilisateur=request.user,
            type_tx="abonnement",
            metadata__app_plan_id=plan.pk,
        )
        if existing_checkout:
            return existing_checkout

        tx = Transaction.objects.create(
            utilisateur=request.user,
            type_tx="abonnement",
            methode="campay",
            montant=plan.price_xaf,
            devise="XAF",
            statut="initie",
            metadata={
                "immigration97_app_key": "prep",
                "app_plan_id": plan.pk,
                "app_plan_slug": plan.slug,
            },
        )
        subscription = AppSubscription.objects.create(
            user=request.user,
            plan=plan,
            status="pending",
            payment_ref=tx.reference,
            notes="Paiement CamPay confirmé séparément; activation manuelle requise.",
        )
        payment = PaymentHistory.objects.create(
            user=request.user,
            subscription=subscription,
            amount_xaf=plan.price_xaf,
            method="campay",
            reference=tx.reference,
            status="pending",
            description=f"CamPay — Immigration97 Premium — {plan.name} ({plan.duration_days} jours)",
        )
        metadata = dict(tx.metadata or {})
        metadata["app_payment_history_id"] = payment.pk
        metadata["app_subscription_id"] = subscription.pk
        tx.metadata = metadata
        tx.save(update_fields=["metadata"])

    return _start_campay_checkout(
        request,
        tx,
        description=f"Immigration97 Premium - {plan.name}",
        fallback_url=fallback_url,
    )


def _set_app_plan_payment_status(transaction_obj, status):
    metadata = transaction_obj.metadata or {}
    payment_id = metadata.get("app_payment_history_id")
    subscription_id = metadata.get("app_subscription_id")
    if not payment_id and not subscription_id:
        return
    from accounts.models import AppSubscription, PaymentHistory

    if payment_id:
        PaymentHistory.objects.filter(pk=payment_id).update(status=status)
    if status == "failed" and subscription_id:
        AppSubscription.objects.filter(pk=subscription_id, status="pending").update(
            status="cancelled"
        )


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
        tx   = Transaction.objects.exclude(methode="campay").filter(ref_operateur=ref).first()

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


@csrf_exempt
def campay_webhook(request):
    """Treat incoming callbacks as hints; only the CamPay status API is authoritative."""
    if request.method == "GET":
        data = request.GET
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({"error": "Invalid payload"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

    provider_reference = data.get("reference") or data.get("transaction_reference")
    if not isinstance(provider_reference, str) or not provider_reference:
        return JsonResponse({"error": "Missing transaction reference"}, status=400)

    tx = Transaction.objects.filter(
        methode="campay",
        ref_operateur=provider_reference,
    ).first()
    if tx is None:
        tx = Transaction.objects.filter(
            methode="campay",
            reference=provider_reference,
        ).first()
    if tx is None:
        return JsonResponse({"error": "Unknown transaction"}, status=404)

    try:
        reconcile_transaction(tx)
    except CampayError as exc:
        logger.warning(
            "CamPay webhook verification failed for transaction %s: %s",
            tx.reference,
            exc,
        )
        return JsonResponse({"error": "Payment verification unavailable"}, status=503)
    return JsonResponse({"ok": True})


def campay_return(request):
    """Verify the payment with CamPay after its browser redirect."""
    token = request.GET.get("token", "")
    try:
        signed_data = signing.loads(
            token,
            salt="payments.campay.return",
            max_age=7 * 24 * 60 * 60,
        )
    except signing.BadSignature:
        return HttpResponseBadRequest("Invalid or expired CamPay return token.")
    if not isinstance(signed_data, dict) or not isinstance(
        signed_data.get("transaction_id"), int
    ):
        return HttpResponseBadRequest("Invalid CamPay return token.")

    tx = get_object_or_404(
        Transaction,
        pk=signed_data["transaction_id"],
        methode="campay",
    )
    verified = True
    try:
        reconcile_transaction(tx)
    except CampayError as exc:
        verified = False
        logger.warning(
            "CamPay return verification failed for transaction %s: %s",
            tx.reference,
            exc,
        )
        tx.refresh_from_db()

    return render(request, "payments/campay_result.html", {
        "transaction": tx,
        "verified": verified,
        "is_immigration97_plan": (
            (tx.metadata or {}).get("immigration97_app_key") == "prep"
        ),
        "refresh_url": request.get_full_path(),
        "whatsapp_payment_url": payment_request_url(
            brand=getattr(request, "site_brand", "E-Shelle"),
            service=_campay_transaction_label(tx),
            amount=f"{tx.montant:.0f} {tx.devise}",
            user=tx.utilisateur,
            details=f"Référence {getattr(request, 'site_brand', 'E-Shelle')} {tx.reference} — validation manuelle après paiement CamPay.",
        ),
    })


def _campay_transaction_label(transaction_obj):
    if transaction_obj.commande_id:
        return f"Validation commande Boutique {transaction_obj.commande.reference}"
    if transaction_obj.formation_id:
        return f"Validation inscription formation {transaction_obj.formation.titre}"
    metadata = transaction_obj.metadata or {}
    app_plan_id = metadata.get("app_plan_id")
    if metadata.get("immigration97_app_key") == "prep" and app_plan_id:
        from accounts.models import AppPlan

        plan = AppPlan.objects.filter(pk=app_plan_id).first()
        return f"Validation du pass Immigration97 Premium {plan.name}" if plan else "Validation du pass Immigration97 Premium"
    plan_name = metadata.get("plan_nom", "Premium")
    return f"Validation pack {plan_name}"


@login_required
def payer_formation(request, formation_id):
    """Paiement d'une formation payante via Mobile Money."""
    from formations.models import Formation, Inscription

    formation = get_object_or_404(Formation, pk=formation_id, is_published=True)
    if formation.prix <= 0:
        messages.info(request, "Cette formation est gratuite.")
        return redirect("formations:detail", slug=formation.slug)

    # Déjà inscrit ?
    if Inscription.objects.filter(utilisateur=request.user, formation=formation).exists():
        messages.info(request, "Vous êtes déjà inscrit à cette formation.")
        return redirect("formations:detail", slug=formation.slug)

    message = (
        f"Bonjour {getattr(request, 'site_brand', 'E-Shelle')} 👋,\n\n"
        f"Je souhaite m'inscrire à la formation suivante :\n\n"
        f"Formation : {formation.titre}\n"
        f"Prix : {formation.prix:.0f} FCFA\n\n"
        f"Client : {request.user.get_full_name() or request.user.username} ({request.user.email})\n\n"
        f"Merci de m'envoyer les instructions de paiement et mon lien d'accès à la formation après réception du paiement 🙏"
    )

    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message, number="237693649944" if getattr(request, "is_immigration97", False) else None)
    return _render_payment_choice(
        request,
        title=formation.titre,
        amount=formation.prix,
        campay_url=reverse("payments:campay_formation", kwargs={"formation_id": formation.pk}),
        whatsapp_payment_url=whatsapp_payment_url,
    )


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
            brand=getattr(request, "site_brand", "E-Shelle"),
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
    """Offer CamPay checkout alongside the existing manual WhatsApp path."""
    from .models import PlanPremiumApp

    module_labels = dict(PlanPremiumApp.MODULE_CHOICES)
    if module not in module_labels:
        messages.error(request, "Module invalide.")
        return redirect("home")

    plans = _get_plans_for_module(module)
    if plan_slug not in plans:
        messages.error(request, "Paramètres invalides.")
        return redirect("home")

    plan = plans[plan_slug]
    module_label = MODULES_LABEL.get(module, module_labels[module])
    
    message = (
        f"Bonjour {getattr(request, 'site_brand', 'E-Shelle')} 👋,\n\n"
        f"Je souhaite activer le Pack Premium suivant :\n\n"
        f"Module : {module_label}\n"
        f"Pack : {plan['nom']} ({plan['duree_jours']} jours)\n"
        f"Prix : {plan['prix']} FCFA\n\n"
        f"Client : {request.user.get_full_name() or request.user.username} ({request.user.email})\n\n"
        f"Merci de valider mon accès Premium après réception du paiement 🙏"
    )

    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message, number="237693649944" if getattr(request, "is_immigration97", False) else None)
    return _render_payment_choice(
        request,
        title=f"{module_label} — Pack {plan['nom']}",
        amount=plan["prix"],
        campay_url=reverse(
            "payments:campay_premium",
            kwargs={"module": module, "plan_slug": plan_slug},
        ),
        whatsapp_payment_url=whatsapp_payment_url,
    )


@login_required
@require_POST
def payer_premium_campay(request, module, plan_slug):
    from .models import PlanPremiumApp

    if module not in dict(PlanPremiumApp.MODULE_CHOICES):
        messages.error(request, "Module invalide.")
        return redirect("home")

    plans = _get_plans_for_module(module)
    if plan_slug not in plans:
        messages.error(request, "Paramètres invalides.")
        return redirect("home")

    plan = plans[plan_slug]
    fallback_url = reverse(
        "payments:payer_premium",
        kwargs={"module": module, "plan_slug": plan_slug},
    )
    with db_transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        existing_checkout = _reuse_existing_campay_checkout(
            request,
            fallback_url,
            amount=plan["prix"],
            utilisateur=request.user,
            metadata__module=module,
            metadata__plan_slug=plan_slug,
        )
        if existing_checkout:
            return existing_checkout

        tx = Transaction.objects.create(
            utilisateur=request.user,
            type_tx="premium_marketplac",
            methode="campay",
            montant=plan["prix"],
            devise="XAF",
            statut="initie",
            metadata={
                "module": module,
                "plan_slug": plan_slug,
                "plan_nom": plan["nom"],
                "duree_jours": plan["duree_jours"],
            },
        )
    return _start_campay_checkout(
        request,
        tx,
        description=f"E-Shelle Premium {module} {plan_slug}",
        fallback_url=fallback_url,
    )


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
        f"Bonjour {getattr(request, 'site_brand', 'E-Shelle')} 👋,\n\n"
        f"Je souhaite booster mon annonce suivante :\n\n"
        f"Annonce : {annonce.titre} (ID #{annonce.pk})\n"
        f"Option de boost : {boost_info['nom']}\n"
        f"Prix : {boost_info['prix']} FCFA\n\n"
        f"Vendeur : {request.user.get_full_name() or request.user.username} ({request.user.email})\n\n"
        f"Merci d'activer le boost après réception du paiement 🙏"
    )

    from core.whatsapp import whatsapp_url
    whatsapp_payment_url = whatsapp_url(message, number="237693649944" if getattr(request, "is_immigration97", False) else None)

    messages.success(request, "Redirection vers WhatsApp pour finaliser le boost de votre annonce...")
    return redirect(whatsapp_payment_url)
