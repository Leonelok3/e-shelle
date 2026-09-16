"""Atomic reservations shared by every AdGen Studio entry point."""
from datetime import timedelta
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from accounts.models import AppSubscription
from adgen.models import StudioUsage
from adgen.studio_plans import STUDIO_PLANS, LEGACY_LIMITS, RESOURCE_LABELS


class StudioLimitError(ValueError):
    pass


TRIAL_USES = 3
TRIAL_LIMITS = {"text": 1, "video": 1, "voice": 1000, "music": 1}


def has_paid_access(user):
    if user.is_staff or user.is_superuser:
        return True
    sub = AppSubscription.get_active_for_user(user, "adgen")
    return bool(sub and sub.status == "active" and not sub.plan.is_free and sub.plan.price_xaf > 0)


def trial_remaining(user):
    used = StudioUsage.objects.filter(user=user, is_trial=True).exclude(status="released").count()
    return max(0, TRIAL_USES - used)


def limits_for(user):
    if user.is_staff or user.is_superuser:
        return {key: 1000000 for key in RESOURCE_LABELS}
    sub = AppSubscription.get_active_for_user(user, "adgen")
    if not has_paid_access(user):
        return TRIAL_LIMITS
    limits = STUDIO_PLANS.get(sub.plan.slug) or LEGACY_LIMITS.get(sub.plan.slug)
    if not limits:
        raise StudioLimitError("Ce forfait nécessite une configuration de quotas par E-Shelle.")
    return limits


def usage_for(user):
    return dict(StudioUsage.objects.filter(user=user, is_trial=False, created_at__gt=timezone.now() - timedelta(days=30))
                .exclude(status="released").values("resource").annotate(total=Sum("amount"))
                .values_list("resource", "total"))


def reserve(user, resource, amount=1, campaign=None, key=None):
    if resource not in RESOURCE_LABELS or amount <= 0:
        raise ValueError("Invalid resource or amount")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        limits = limits_for(user)
        if key and StudioUsage.objects.filter(user=user, request_key=key).exists():
            raise StudioLimitError("Cette demande a déjà été prise en compte. Consultez votre bibliothèque.")
        if StudioUsage.objects.filter(user=user, resource=resource, status__in=["reserved", "running"]).exists():
            raise StudioLimitError("Une génération de ce type est déjà en cours. Attendez sa fin.")
        if not has_paid_access(user):
            if trial_remaining(user) <= 0:
                raise StudioLimitError("Vos 3 utilisations gratuites sont épuisées. Choisissez un abonnement AdGen pour continuer.")
            if amount > TRIAL_LIMITS[resource]:
                raise StudioLimitError("L’essai autorise une génération à la fois et 1 000 caractères maximum par voix-off.")
            return StudioUsage.objects.create(user=user, resource=resource, amount=amount,
                campaign=campaign, request_key=key or str(uuid4()), is_trial=True)
        used = usage_for(user).get(resource, 0)
        if used + amount > limits[resource]:
            raise StudioLimitError(f"Quota atteint : {used}/{limits[resource]} {RESOURCE_LABELS[resource]} sur 30 jours. Consultez vos abonnements.")
        return StudioUsage.objects.create(user=user, resource=resource, amount=amount,
                                         campaign=campaign, request_key=key or str(uuid4()))


def finish(reservation, *, failed=False, release=False):
    # Uncertain API failures consume the attempt allowance; local failures release it.
    StudioUsage.objects.filter(pk=reservation.pk, status__in=["reserved", "running"]).update(
        status="released" if release else "failed" if failed else "consumed")


def summary_for(user):
    if not has_paid_access(user):
        remaining = trial_remaining(user)
        return [dict(label="Utilisations gratuites (tous outils confondus)", used=TRIAL_USES - remaining,
                     limit=TRIAL_USES, remaining=remaining, is_trial=True)]
    try:
        limits = limits_for(user)
    except StudioLimitError:
        return []
    used = usage_for(user)
    return [dict(label=label, used=used.get(key, 0), limit=limits[key],
                 remaining=max(0, limits[key] - used.get(key, 0))) for key, label in RESOURCE_LABELS.items()]
