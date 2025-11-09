# billing/views.py
import random
import string
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from .models import SubscriptionPlan, CreditCode, Subscription, Transaction
from .services import activate_pass, has_active_access, grant_session_access, has_session_access

import random
import string
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CreditCode, SubscriptionPlan

@login_required
def generate_code(request):
    """
    Génère un nouveau code prépayé pour l'utilisateur connecté.
    """
    plans = SubscriptionPlan.objects.filter(is_active=True)

    if request.method == "POST":
        # Récupérer le plan choisi par l'utilisateur
        plan_slug = request.POST.get("plan")
        plan = SubscriptionPlan.objects.filter(slug=plan_slug, is_active=True).first()
        if not plan:
            # Si aucun plan sélectionné ou plan invalide, prendre le premier actif
            plan = plans.first()
        if not plan:
            return render(request, "billing/generate_code.html", {
                "error": "Aucun plan actif n'est disponible.",
                "plans": plans
            })

        # Génération d’un code alphanumérique simple de 12 caractères
        code_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

        # Création du CreditCode
        credit_code = CreditCode.objects.create(
            code=code_str,
            plan=plan
        )

        return render(request, "billing/generate_code.html", {
            "code": credit_code,
            "plans": plans
        })

    # GET : afficher le formulaire
    return render(request, "billing/generate_code.html", {"plans": plans})



def _redirect_next_or(default_path, request):
    nxt = request.GET.get("next") or request.POST.get("next")
    return redirect(nxt if nxt else default_path)


# --- PUBLIC: accessible sans login ---
def access(request):
    """
    Page d'accès (publique) :
    - Si utilisateur connecté => on affiche son expiration si existante.
    - Si invité => on regarde l'accès en session (ex: après un code).
    """
    now = timezone.now()
    active_sub = None
    expires = None

    if request.user.is_authenticated:
        active_sub = (
            Subscription.objects
            .filter(user=request.user, expires_at__gt=now)
            .order_by("-expires_at")
            .first()
        )
        expires = active_sub.expires_at if active_sub else None

    session_active = has_session_access(request)
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price_usd")

    return render(request, "billing/access.html", {
        "expires": expires,
        "session_active": session_active,
        "plans": plans,
        "next": request.GET.get("next", ""),
    })


# --- PUBLIC: achat simulé ---
def buy(request):
    """
    Achat simple (placeholder tant que l'intégration Stripe/PayPal n'est pas branchée) :
    - En mode démo : on "simule" un achat en donnant un accès session 30 min.
    - En prod : remplacer par redirection vers Stripe Checkout / PayPal puis webhook -> grant_session_access(...)
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price_usd")
    if request.method == "POST":
        # DEMO/PLACEHOLDER: active un accès session direct
        grant_session_access(request, minutes=30)
        messages.success(request, "✅ Accès activé pendant 30 minutes pour télécharger en HD.")
        return _redirect_next_or(reverse("billing:access"), request)

    return render(
        request,
        "billing/buy.html",
        {"plans": plans, "next": request.GET.get("next", "")},
    )


def redeem(request):
    """
    Validation d'un code d'accès :
    - Vérifie si le code est valide (non expiré et non utilisé)
    - Si connecté : lie le code à l'utilisateur et active un plan
    - Si invité : accorde un accès temporaire en session
    """
    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()

        try:
            cc = CreditCode.objects.select_related("plan").get(code__iexact=code)
        except CreditCode.DoesNotExist:
            messages.error(request, "❌ Code invalide.")
            return _redirect_next_or(reverse("billing:redeem"), request)

        # Vérification de la validité
        if not cc.is_valid():
            messages.error(request, "❌ Ce code est expiré ou déjà utilisé.")
            return _redirect_next_or(reverse("billing:redeem"), request)

        # Marquer le code comme utilisé
        cc.use(request.user if request.user.is_authenticated else None)

        # Activer l'accès selon le contexte
        if request.user.is_authenticated:
            activate_pass(request.user, cc.plan, source="code", code_used=cc)
            messages.success(request, f"✅ Code validé. Accès {cc.plan.name} activé !")
        else:
            grant_session_access(request, minutes=30)
            messages.success(request, "✅ Code validé. Accès temporaire activé !")

        # Redirection
        return _redirect_next_or(reverse("billing:access"), request)

    return render(
        request,
        "billing/redeem.html",
        {"next": request.GET.get("next", "")},
    )


@login_required
def generate_code(request):
    """
    Génère un code d'accès unique valide 24h ou 30 jours selon le choix.
    """
    if request.method == "POST":
        validity = request.POST.get("validity", "24h")
        plan_slug = request.POST.get("plan")  # optionnel : permet de lier à un plan précis

        expiration_time = (
            timezone.now() + timedelta(hours=24)
            if validity == "24h"
            else timezone.now() + timedelta(days=30)
        )

        # Génération d'un code aléatoire unique
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        plan = None
        if plan_slug:
            plan = SubscriptionPlan.objects.filter(slug=plan_slug).first()

        CreditCode.objects.create(
            code=code,
            plan=plan if plan else SubscriptionPlan.objects.first(),
            expiration_date=expiration_time,
        )

        messages.success(request, f"✅ Code {code} généré avec succès ! Valide jusqu'au {expiration_time:%Y-%m-%d %H:%M}.")
        return redirect("billing:access")

    plans = SubscriptionPlan.objects.filter(is_active=True)
    return render(request, "billing/generate_code.html", {"plans": plans})


@login_required
def wallet_dashboard(request):
    """
    Tableau de bord utilisateur : historique et abonnements.
    """
    now = timezone.now()
    subs = Subscription.objects.filter(user=request.user).order_by("-expires_at")
    txs = Transaction.objects.filter(user=request.user).order_by("-created_at")[:20]
    active = has_active_access(request.user)
    return render(
        request,
        "billing/wallet.html",
        {
            "has_access": active,
            "subscriptions": subs,
            "transactions": txs,
            "now": now,
        },
    )
