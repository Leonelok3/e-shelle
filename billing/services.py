# billing/services.py
from datetime import timedelta
from django.utils import timezone

from .models import Subscription, SubscriptionPlan, CreditCode, Transaction


def has_active_access(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    now = timezone.now()
    return Subscription.objects.filter(user=user, expires_at__gt=now, is_active=True).exists()

def activate_pass(user, plan: SubscriptionPlan, source: str, code_used: CreditCode | None = None):
    """
    Active ou prolonge un pass pour l'utilisateur.
    """
    now = timezone.now()
    sub, created = Subscription.objects.get_or_create(
        user=user,
        plan=plan,
        defaults={
            "starts_at": now,
            "expires_at": now + timedelta(days=plan.duration_days),
            "is_active": True,
        },
    )
    if not created:
        # prolonge si encore actif, sinon redémarre
        if sub.expires_at and sub.expires_at > now:
            sub.expires_at = sub.expires_at + timedelta(days=plan.duration_days)
        else:
            sub.starts_at = now
            sub.expires_at = now + timedelta(days=plan.duration_days)
            sub.is_active = True
    sub.save()

    Transaction.objects.create(
        user=user,
        amount=plan.price_usd,
        currency="USD",
        type="CREDIT",
        description=f"Activation plan {plan.name} via {source}",
        related_code=code_used if code_used else None,
    )
    return sub



    # billing/services.py

# --- EXISTANT: tes fonctions actuelles ici ---
# activate_pass(user, plan, source, code_used=None)
# has_active_access(user)

SESSION_ACCESS_KEY = "billing_session_access_until"


def grant_session_access(request, minutes=30):
    """
    Donne un accès temporaire en session pour les invités (ou en plus pour un user connecté).
    """
    until = timezone.now() + timedelta(minutes=minutes)
    request.session[SESSION_ACCESS_KEY] = until.isoformat()
    request.session.modified = True
    return until


def has_session_access(request):
    """
    True si la session a un accès temporaire non expiré.
    """
    iso = request.session.get(SESSION_ACCESS_KEY)
    if not iso:
        return False
    try:
        until = timezone.datetime.fromisoformat(iso)
        # timezone-aware coercion si besoin
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > timezone.now()
    except Exception:
        return False


def has_access(request):
    """
    Vérifie l'accès global:
    - si user connecté et a un pass actif -> True
    - sinon si session a un accès temporaire -> True
    """
    if request.user.is_authenticated and has_active_access(request.user):
        return True
    return has_session_access(request)

