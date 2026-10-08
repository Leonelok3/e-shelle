"""Plan-gated WhatsApp features for a business profile."""

from django.utils import timezone

from business.models import BusinessProfile


def whatsapp_entitlements(business):
    business.check_expiry()
    eligible = business.subscription_active and business.is_active
    if business.is_trial:
        eligible = eligible and bool(
            business.subscription_expires_at
            and business.subscription_expires_at > timezone.now()
        )

    plan = business.plan if eligible else BusinessProfile.Plan.FREE
    crm = plan in {
        BusinessProfile.Plan.PRO,
        BusinessProfile.Plan.BUSINESS,
        BusinessProfile.Plan.PREMIUM,
    }
    return {
        "plan": plan,
        "can_connect": crm,
        "can_use_crm": crm,
        "can_automate": plan in {
            BusinessProfile.Plan.BUSINESS,
            BusinessProfile.Plan.PREMIUM,
        },
        "can_sync_catalog": plan in {
            BusinessProfile.Plan.BUSINESS,
            BusinessProfile.Plan.PREMIUM,
        },
    }


def require_whatsapp_entitlement(business, feature):
    return bool(whatsapp_entitlements(business).get(feature, False))
