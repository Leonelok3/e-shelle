"""
accounts/context_processors.py
================================
Injecte automatiquement l'état des abonnements de l'utilisateur
dans TOUS les templates de la plateforme.

Activation dans settings.py :
    TEMPLATES[0]["OPTIONS"]["context_processors"] += [
        "accounts.context_processors.subscription_context",
    ]

Variables disponibles dans chaque template :
    {{ user_subs }}              → dict {app_key: AppSubscription}
    {{ user_subs.adgen }}        → l'abonnement AdGen actif (ou None)
    {{ user_subs.rencontres }}   → l'abonnement Rencontres actif
    {% if user_subs.edo %}       → True si abonné EduCam
    {{ active_sub_count }}       → nombre total d'abonnements actifs
    {{ has_any_paid_sub }}       → True si au moins un abo payant actif
"""

from .models import AppSubscription, AppKey


def subscription_context(request):
    """Context processor principal — performances optimisées."""
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "user_subs": {},
            "active_sub_count": 0,
            "has_any_paid_sub": False,
        }

    # Cache au niveau de la requête pour éviter plusieurs requêtes DB
    if not hasattr(request, "_eshelle_subs_cache"):
        subs_qs = (
            AppSubscription.objects
            .filter(user=request.user)
            .select_related("plan")
            .order_by("plan__app_key", "-started_at")
        )

        # On garde un seul abonnement par app (le plus récent actif)
        subs_map = {}
        for sub in subs_qs:
            key = sub.plan.app_key
            if key not in subs_map and sub.is_active:
                subs_map[key] = sub

        request._eshelle_subs_cache = subs_map

    subs_map = request._eshelle_subs_cache
    paid_apps = {k for k, v in subs_map.items() if v.plan.price_xaf > 0}

    return {
        "user_subs": subs_map,
        "active_sub_count": len(subs_map),
        "has_any_paid_sub": bool(paid_apps),
    }


def social_login_context(request):
    """Expose l'etat des connexions sociales sans faire casser les pages auth."""
    try:
        from allauth.socialaccount.models import SocialApp
        from django.conf import settings

        google_in_settings = False
        google_prov = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get("google", {})
        if "APP" in google_prov and google_prov["APP"].get("client_id"):
            google_in_settings = True

        facebook_in_settings = False
        facebook_prov = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get("facebook", {})
        if "APP" in facebook_prov and facebook_prov["APP"].get("client_id"):
            facebook_in_settings = True

        # Expose the absolute next URL for social login to ensure it redirects back to the subdomain
        next_path = request.GET.get('next', '/')
        if next_path.startswith('/'):
            absolute_next = request.build_absolute_uri(next_path)
        else:
            absolute_next = next_path

        # Check if the user has a business profile
        user_has_business = False
        if request.user.is_authenticated:
            try:
                from business.models import BusinessProfile
                user_has_business = BusinessProfile.objects.filter(owner=request.user).exists()
            except Exception:
                pass

        return {
            "social_google_enabled": google_in_settings or SocialApp.objects.filter(provider="google").exists(),
            "social_facebook_enabled": facebook_in_settings or SocialApp.objects.filter(provider="facebook").exists(),
            "social_next_url": absolute_next,
            "SITE_URL": getattr(settings, "SITE_URL", "https://e-shelle.com").rstrip('/'),
            "user_has_business": user_has_business,
        }
    except Exception:
        return {
            "social_google_enabled": False,
            "social_facebook_enabled": False,
            "social_next_url": "/",
            "SITE_URL": "https://e-shelle.com",
            "user_has_business": False,
        }

