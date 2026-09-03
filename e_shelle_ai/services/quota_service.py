"""
e_shelle_ai/services/quota_service.py
Gestion des quotas mensuels par utilisateur.
Mappe le plan UserProfile (free/pro/enterprise) → limites IA.
"""
import logging
from datetime import date

logger = logging.getLogger(__name__)


# Limites par plan
PLAN_LIMITS = {
    "free":       {"messages": 200,   "images": 50},
    "starter":    {"messages": 200,   "images": 50},
    "pro":        {"messages": 500,   "images": 50},
    "enterprise": {"messages": 99999, "images": 9999},
}

ADGEN_SUBSCRIPTION_LIMITS = {
    "adgen-starter":  {"plan": "starter",    "messages": 300,  "images": 10},
    "adgen-pro":      {"plan": "pro",        "messages": 1500, "images": 50},
    "adgen-business": {"plan": "enterprise", "messages": 5000, "images": 150},
}

# Mapping plan UserProfile → plan IA
PROFILE_TO_AI_PLAN = {
    "free":       "starter",
    "pro":        "pro",
    "enterprise": "enterprise",
}


class QuotaService:
    """Service de gestion des quotas IA utilisateur."""

    def _get_or_create_quota(self, user):
        """Récupère ou crée le quota de l'utilisateur, en le synchronisant avec son plan."""
        from e_shelle_ai.models import AIQuota

        adgen_limits = self._get_adgen_subscription_limits(user)
        if adgen_limits:
            ai_plan = adgen_limits["plan"]
            limits = {
                "messages": adgen_limits["messages"],
                "images": adgen_limits["images"],
            }
        else:
            ai_plan, limits = self._get_profile_limits(user)

        quota, created = AIQuota.objects.get_or_create(
            user=user,
            defaults={
                "plan":           ai_plan,
                "messages_limit": limits["messages"],
                "images_limit":   limits["images"],
                "reset_date":     self._next_reset_date(),
            }
        )

        if not created:
            # Synchroniser le plan ou les limites si configurés différemment
            if (quota.plan != ai_plan or
                quota.messages_limit != limits["messages"] or
                quota.images_limit != limits["images"]):
                quota.plan           = ai_plan
                quota.messages_limit = limits["messages"]
                quota.images_limit   = limits["images"]
                quota.save(update_fields=["plan", "messages_limit", "images_limit"])
            # Reset mensuel si nécessaire
            quota.check_and_reset_if_needed()

        return quota

    def _get_profile_limits(self, user):
        """Limites IA historiques basees sur le profil E-Shelle global."""
        # Détecter le plan actuel depuis UserProfile
        profile_plan = "free"
        try:
            profile = user.profile
            profile_plan = profile.plan or "free"
            # Vérifier si plan expiré
            if profile.plan_expiry and profile.plan_expiry < date.today():
                profile_plan = "free"
        except Exception:
            pass

        ai_plan = PROFILE_TO_AI_PLAN.get(profile_plan, "starter")
        limits = PLAN_LIMITS.get(ai_plan, PLAN_LIMITS["starter"])
        return ai_plan, limits

    def _get_adgen_subscription_limits(self, user):
        """Retourne les limites AdGen payantes, afin qu'un client ne depasse jamais son forfait."""
        try:
            from accounts.models import AppSubscription

            sub = AppSubscription.get_active_for_user(user, "adgen")
            if not sub or sub.status != "active" or sub.plan.is_free or sub.plan.price_xaf <= 0:
                return None
            return ADGEN_SUBSCRIPTION_LIMITS.get(sub.plan.slug)
        except Exception as exc:
            logger.warning(f"AdGen subscription quota lookup failed pour {user}: {exc}")
            return None

    def _next_reset_date(self):
        """Retourne le 1er du mois prochain."""
        today = date.today()
        if today.month == 12:
            return date(today.year + 1, 1, 1)
        return date(today.year, today.month + 1, 1)

    def check_message_quota(self, user) -> bool:
        """True si l'utilisateur peut encore envoyer un message ce mois."""
        try:
            quota = self._get_or_create_quota(user)
            return quota.messages_used < quota.messages_limit
        except Exception as e:
            logger.error(f"Quota check error pour {user}: {e}")
            return True  # Permissif en cas d'erreur technique

    def check_image_quota(self, user) -> bool:
        """True si l'utilisateur peut encore générer une image ce mois."""
        try:
            quota = self._get_or_create_quota(user)
            return quota.images_used < quota.images_limit
        except Exception as e:
            logger.error(f"Image quota check error pour {user}: {e}")
            return False

    def increment_usage(self, user, type: str = "message"):
        """
        Incrémente le compteur après utilisation.
        type: 'message' | 'image'
        """
        try:
            quota = self._get_or_create_quota(user)
            if type == "message":
                quota.messages_used += 1
                quota.save(update_fields=["messages_used"])
            elif type == "image":
                quota.images_used += 1
                quota.save(update_fields=["images_used"])
        except Exception as e:
            logger.error(f"Quota increment error pour {user}: {e}")

    def get_remaining(self, user) -> dict:
        """Retourne {'messages': 47, 'images': 12, 'plan': 'pro'}."""
        try:
            quota = self._get_or_create_quota(user)
            return {
                "messages":  quota.messages_remaining,
                "images":    quota.images_remaining,
                "plan":      quota.plan,
                "msg_used":  quota.messages_used,
                "msg_limit": quota.messages_limit,
                "img_used":  quota.images_used,
                "img_limit": quota.images_limit,
            }
        except Exception:
            return {"messages": 0, "images": 0, "plan": "starter", "msg_used": 0, "msg_limit": 30}

    def get_upgrade_message(self, user, type: str = "message") -> str:
        """Message d'invitation à upgrader quand le quota est atteint."""
        quota = self._get_or_create_quota(user)
        if quota.plan == "starter":
            return (
                "Vous avez atteint votre limite mensuelle. "
                "Passez au plan AdGen Pro pour continuer a generer plus de publicites. "
                "Contactez-nous sur WhatsApp pour souscrire."
            )
        elif quota.plan == "pro":
            return (
                "Limite mensuelle Pro atteinte. "
                "Passez au plan AdGen Business pour augmenter votre volume."
            )
        return "Limite atteinte. Contactez le support E-Shelle."
