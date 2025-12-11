# billing/views.py
import random
import string
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.db import IntegrityError

from .models import SubscriptionPlan, CreditCode, Subscription, Transaction
from .services import activate_pass, has_active_access, grant_session_access, has_session_access


def _redirect_next_or(default_path, request):
    """Helper pour redirection avec next"""
    nxt = request.GET.get("next") or request.POST.get("next")
    return redirect(nxt if nxt else default_path)


# =============================================================================
# PAGES PUBLIQUES
# =============================================================================

def pricing(request):
    """Page de tarification - Affiche tous les plans disponibles"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('order', 'duration_days')
    has_active_sub = False
    if request.user.is_authenticated:
        has_active_sub = has_active_access(request.user)
    
    return render(request, "billing/pricing.html", {
        "plans": plans,
        "has_active_sub": has_active_sub,
        "next": request.GET.get("next", ""),
    })


def access(request):
    """Page d'accès - Statut de l'abonnement"""
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
        "active_subscription": active_sub,
        "session_active": session_active,
        "plans": plans,
        "next": request.GET.get("next", ""),
    })


# =============================================================================
# ACHAT - Placeholder pour Cinetpay/Stripe
# =============================================================================

def buy(request):
    """Page d'achat simple (temporaire)"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price_usd")
    if request.method == "POST":
        grant_session_access(request, minutes=30)
        messages.success(request, "✅ Accès activé pendant 30 minutes (DEMO).")
        return _redirect_next_or(reverse("billing:access"), request)

    return render(request, "billing/buy.html", {"plans": plans, "next": request.GET.get("next", "")})


# =============================================================================
# CODES PRÉPAYÉS
# =============================================================================

@login_required
def generate_code(request):
    """Génère un code prépayé (admin uniquement)"""
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect("billing:pricing")
    
    plans = SubscriptionPlan.objects.filter(is_active=True)

    if request.method == "POST":
        plan_slug = request.POST.get("plan")
        quantity = int(request.POST.get("quantity", 1))
        
        plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
        
        generated_codes = []
        for _ in range(quantity):
            # Utiliser la méthode generate_unique du modèle pour éviter collisions
            tries = 0
            while True:
                tries += 1
                code_str = CreditCode.generate_unique()
                try:
                    credit_code = CreditCode.objects.create(
                        code=code_str,
                        plan=plan,
                        expiration_date=timezone.now() + timedelta(days=90),
                        created_by_affiliate=None
                    )
                    generated_codes.append(credit_code)
                    break
                except IntegrityError:
                    # très rare, on retente (surtout si génération en concurrence)
                    if tries >= 5:
                        # si échec multiple, remonter une erreur pour debug/admin
                        messages.error(request, "Erreur lors de la génération d'un code (collision répétée).")
                        break
                    continue

        return render(request, "billing/generate_code.html", {"codes": generated_codes, "plans": plans})

    return render(request, "billing/generate_code.html", {"plans": plans})


def redeem(request):
    """Validation d'un code d'accès"""
    if request.method == "POST":
        code = (request.POST.get("code") or "").strip().upper()
        try:
            cc = CreditCode.objects.select_related("plan").get(code__iexact=code)
        except CreditCode.DoesNotExist:
            messages.error(request, "❌ Code invalide.")
            return _redirect_next_or(reverse("billing:redeem"), request)

        if not cc.is_valid():
            messages.error(request, "❌ Ce code est expiré ou déjà utilisé.")
            return _redirect_next_or(reverse("billing:redeem"), request)

        try:
            cc.use(request.user if request.user.is_authenticated else None)
        except ValueError as e:
            messages.error(request, f"❌ {str(e)}")
            return _redirect_next_or(reverse("billing:redeem"), request)

        if request.user.is_authenticated:
            activate_pass(request.user, cc.plan, source="code", code_used=cc)
            messages.success(request, f"✅ Code validé ! Accès {cc.plan.name} activé.")
        else:
            grant_session_access(request, minutes=30)
            messages.success(request, "✅ Code validé ! Accès temporaire activé.")

        return _redirect_next_or(reverse("billing:access"), request)

    return render(request, "billing/redeem.html", {"next": request.GET.get("next", "")})


# =============================================================================
# TABLEAU DE BORD
# =============================================================================

@login_required
def wallet_dashboard(request):
    """Tableau de bord utilisateur : abonnements et transactions"""
    now = timezone.now()
    
    active_sub = (
        Subscription.objects
        .filter(user=request.user, expires_at__gt=now)
        .select_related("plan")
        .order_by("-expires_at")
        .first()
    )
    
    subscriptions = (
        Subscription.objects
        .filter(user=request.user)
        .select_related("plan")
        .order_by("-starts_at")[:10]
    )
    
    transactions = (
        Transaction.objects
        .filter(user=request.user)
        .select_related("plan")
        .order_by("-created_at")[:20]
    )
    
    codes_used = (
        CreditCode.objects
        .filter(used_by=request.user)
        .select_related("plan")
        .order_by("-used_at")[:10]
    )
    
    return render(request, "billing/wallet.html", {
        "active_subscription": active_sub,
        "subscriptions": subscriptions,
        "transactions": transactions,
        "codes_used": codes_used,
        "has_access": active_sub is not None,
        "now": now,
    })


@login_required
def buy_plan(request, plan_slug):
    """Page de sélection de la méthode de paiement"""
    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
    
    # Créer une transaction PENDING
    transaction = Transaction.objects.create(
        user=request.user,
        plan=plan,
        amount=plan.price_usd,
        currency="USD",
        type="CREDIT",
        status="PENDING",
        description=f"Achat {plan.name}",
    )
    
    context = {
        "plan": plan,
        "transaction": transaction,
        "cinetpay_available": False,  # Sera True quand vous configurerez Cinetpay
        "stripe_available": False,    # Sera True quand vous configurerez Stripe
        "next": request.GET.get("next", ""),
    }
    
    return render(request, "billing/buy_plan.html", context)

@login_required
def initiate_payment(request, transaction_id):
    """
    Initie le paiement selon la méthode choisie
    TEMPORAIRE : Redirige vers la page de confirmation pour l'instant
    """
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    
    if transaction.status != "PENDING":
        messages.error(request, "Cette transaction a déjà été traitée.")
        return redirect("billing:wallet")
    
    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        
        # Pour le moment, on affiche juste un message
        # Plus tard, on intégrera vraiment Cinetpay/Stripe ici
        messages.info(
            request, 
            f"Paiement {payment_method} sélectionné. "
            "L'intégration des paiements sera activée prochainement. "
            "Utilisez un code prépayé pour le moment."
        )
        return redirect("billing:redeem")
    
    return redirect("billing:buy_plan", plan_slug=transaction.plan.slug)
