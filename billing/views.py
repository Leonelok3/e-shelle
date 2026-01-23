# billing/views.py
from datetime import timedelta
from decimal import Decimal
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .forms import WalletReloadForm
from .models import SubscriptionPlan, CreditCode, Subscription, Transaction
from .services import (
    activate_pass,  # garde si tu l'utilises ailleurs
    has_active_access,
    grant_session_access,
    has_session_access,
)

# ✅ Parrainage / Commissions (affiliate)
# Si ce fichier n'existe pas encore, crée-le (je peux te le renvoyer).
from .affiliates import create_commission_for_transaction


def _redirect_next_or(default_path, request):
    nxt = request.GET.get("next") or request.POST.get("next")
    return redirect(nxt if nxt else default_path)


def rate_limit_redeem(request, limit=5, window_seconds=60):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    key = f"redeem:{ip}"
    current = cache.get(key, 0)

    if current >= limit:
        return True

    try:
        if current == 0:
            cache.set(key, 1, timeout=window_seconds)
        else:
            cache.incr(key)
    except Exception:
        cache.set(key, current + 1, timeout=window_seconds)

    return False


# =============================================================================
# PAGES PUBLIQUES
# =============================================================================

def pricing(request):
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("order", "duration_days")
    has_active_sub = request.user.is_authenticated and has_active_access(request.user)

    return render(request, "billing/pricing.html", {
        "plans": plans,
        "has_active_sub": has_active_sub,
        "next": request.GET.get("next", ""),
    })


def access(request):
    now = timezone.now()
    active_sub = None
    expires = None

    if request.user.is_authenticated:
        active_sub = (
            Subscription.objects
            .filter(user=request.user, expires_at__gt=now)
            .select_related("plan")
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
# ACHAT - DEMO
# =============================================================================

def buy(request):
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price_usd")
    if request.method == "POST":
        grant_session_access(request, minutes=30)
        messages.success(request, "✅ Accès activé pendant 30 minutes (DEMO).")
        return _redirect_next_or(reverse("billing:access"), request)

    return render(request, "billing/buy.html", {
        "plans": plans,
        "next": request.GET.get("next", ""),
    })


# =============================================================================
# CODES PRÉPAYÉS (STAFF)
# =============================================================================

@login_required
def generate_code(request):
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect("billing:pricing")

    plans = SubscriptionPlan.objects.filter(is_active=True)

    if request.method == "POST":
        plan_slug = request.POST.get("plan")
        quantity = int(request.POST.get("quantity", 1))
        quantity = min(max(quantity, 1), 1000)

        plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)

        batch_id = str(uuid.uuid4())[:8]
        expires_at = timezone.now() + timedelta(days=90)

        generated_codes = []
        for _ in range(quantity):
            tries = 0
            while True:
                tries += 1
                code_str = CreditCode.generate_unique()
                try:
                    credit_code = CreditCode.objects.create(
                        code=code_str,
                        plan=plan,
                        expiration_date=expires_at,
                        created_by_staff=request.user,
                        batch_id=batch_id,
                        notes=f"Généré via vue staff (batch {batch_id})",
                        max_uses=1,
                    )
                    generated_codes.append(credit_code)
                    break
                except IntegrityError:
                    if tries >= 5:
                        messages.error(request, "Erreur génération code (collision répétée).")
                        break

        return render(request, "billing/generate_code.html", {
            "codes": generated_codes,
            "plans": plans,
            "batch_id": batch_id,
        })

    return render(request, "billing/generate_code.html", {"plans": plans})


# =============================================================================
# REDEEM (CODES)
# =============================================================================

def redeem(request):
    if request.method == "POST":
        if rate_limit_redeem(request, limit=5, window_seconds=60):
            messages.error(request, "⛔ Trop de tentatives. Réessaie dans 1 minute.")
            return _redirect_next_or(reverse("billing:redeem"), request)

        code = (request.POST.get("code") or "").strip().upper()
        if not code:
            messages.error(request, "❌ Entre un code.")
            return _redirect_next_or(reverse("billing:redeem"), request)

        try:
            cc = CreditCode.objects.select_related("plan").get(code__iexact=code)
        except CreditCode.DoesNotExist:
            messages.error(request, "❌ Code invalide.")
            return _redirect_next_or(reverse("billing:redeem"), request)

        try:
            cc.use(
                user=request.user if request.user.is_authenticated else None,
                ip=request.META.get("REMOTE_ADDR"),
            )
        except ValueError as e:
            messages.error(request, f"❌ {str(e)}")
            return _redirect_next_or(reverse("billing:redeem"), request)

        if request.user.is_authenticated:
            sub, created = Subscription.activate_or_extend(user=request.user, plan=cc.plan)

            # ✅ TX COMPLETED (base commission = prix plan même si amount=0)
            tx = Transaction.objects.create(
                user=request.user,
                plan=cc.plan,
                amount=Decimal("0.00"),
                currency="USD",
                type="CREDIT",
                status="COMPLETED",
                payment_method="CODE",
                description=f"Activation via code {cc.code}",
                related_code=cc,
                related_subscription=sub,
                metadata={
                    "stacking": True,
                    "created_new_subscription": created,
                    "ip": request.META.get("REMOTE_ADDR"),
                    "code": cc.code,
                    "commission_base": str(cc.plan.price_usd),  # ✅ pour parrainage sur codes
                },
            )

            # ✅ Commission si le user a été parrainé
            create_commission_for_transaction(tx)

            messages.success(
                request,
                f"✅ Code validé ! Accès activé jusqu’au {sub.expires_at.strftime('%d/%m/%Y %H:%M')}."
            )
        else:
            grant_session_access(request, minutes=60)
            messages.success(request, "✅ Code validé ! Accès temporaire activé (1h).")

        return _redirect_next_or(reverse("billing:access"), request)

    return render(request, "billing/redeem.html", {"next": request.GET.get("next", "")})


# =============================================================================
# DASHBOARD WALLET
# =============================================================================

@login_required
def wallet_dashboard(request):
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
        "wallet": None,  # pour tes templates
    })


# =============================================================================
# FLOW PAIEMENT (placeholder)
# =============================================================================

@login_required
def buy_plan(request, plan_slug):
    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)

    tx = Transaction.objects.create(
        user=request.user,
        plan=plan,
        amount=plan.price_usd,
        currency="USD",
        type="CREDIT",
        status="PENDING",
        description=f"Achat {plan.name}",
        payment_method="OTHER",
    )

    return render(request, "billing/buy_plan.html", {
        "plan": plan,
        "transaction": tx,
        "cinetpay_available": False,
        "stripe_available": False,
        "next": request.GET.get("next", ""),
    })


@login_required
def initiate_payment(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)

    if tx.status != "PENDING":
        messages.error(request, "Cette transaction a déjà été traitée.")
        return redirect("billing:wallet")

    if request.method == "POST":
        payment_method = request.POST.get("payment_method") or "OTHER"
        tx.payment_method = payment_method
        tx.save(update_fields=["payment_method"])

        # ⚠️ Ici tu feras le redirect vers CinetPay/Stripe.
        # Quand tu recevras la confirmation (webhook), tu feras:
        # tx.status = "COMPLETED"; tx.save(); create_commission_for_transaction(tx)

        messages.info(
            request,
            f"Paiement {payment_method} sélectionné. "
            "L'intégration des paiements sera activée prochainement. "
            "Utilisez un code prépayé pour le moment."
        )
        return redirect("billing:redeem")

    return redirect("billing:buy_plan", plan_slug=tx.plan.slug)


# =============================================================================
# RECHARGE WALLET (DEMO)
# =============================================================================

@login_required
def reload_wallet(request):
    form = WalletReloadForm(request.POST or None)
    wallet = None

    if request.method == "POST":
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            note = form.cleaned_data.get("note") or ""

            tx = Transaction.objects.create(
                user=request.user,
                plan=None,
                amount=Decimal(amount),
                currency="USD",
                type="CREDIT",
                status="COMPLETED",
                payment_method="WALLET_TOPUP",
                description="Recharge wallet (DEMO)",
                metadata={
                    "note": note,
                    "at": timezone.now().isoformat(),
                    "ip": request.META.get("REMOTE_ADDR"),
                },
            )

            # ✅ Optionnel : commission si tu veux récompenser aussi les recharges
            # Si tu ne veux PAS de commission sur wallet, supprime la ligne suivante.
            create_commission_for_transaction(tx)

            messages.success(request, f"✅ Recharge enregistrée : +{amount} USD (DEMO).")
            return redirect("billing:wallet")

        messages.error(request, "❌ Vérifie le montant et réessaie.")

    return render(request, "billing/reload.html", {"form": form, "wallet": wallet})
