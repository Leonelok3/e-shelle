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


def german_profile_context(request):
    """
    Injecte le profil d'allemand de l'utilisateur, sa progression (%),
    et des conseils d'amélioration personnalisés dans tous les templates.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "german_profile": None,
            "german_level_progress": 0,
            "german_evolution_tips": [],
            "is_german_space": False,
        }

    path = request.path
    is_german_space = "/allemand/" in path or "/allemagne/" in path or "/lebenslauf/" in path

    try:
        from GermanPrepApp.models import GermanUserProfile
        
        # Récupérer ou créer le profil allemand
        profile, created = GermanUserProfile.objects.get_or_create(user=request.user)
        
        # Calculer le pourcentage de progression vers le niveau suivant
        lvl = profile.level
        xp = profile.xp
        
        # Seuils de niveau définis dans compute_level
        thresholds = {
            1: (0, 100),
            2: (100, 250),
            3: (250, 500),
            4: (500, 900),
            5: (900, 1400),
        }
        
        if lvl in thresholds:
            low, high = thresholds[lvl]
        else:
            low = 1400 + (lvl - 6) * 400
            high = low + 400
            
        range_xp = high - low
        user_xp_in_level = xp - low
        
        progress = 0
        if range_xp > 0:
            progress = min(max(int((user_xp_in_level / range_xp) * 100), 0), 100)
            
        # Conseils dynamiques d'amélioration
        tips = []
        if not profile.placement_level:
            tips.append("🎯 Évalue ton niveau de départ en faisant le test de niveau d'allemand.")
        else:
            tips.append(f"💪 Niveau conseillé : {profile.placement_level}. Entraîne-toi sur ce niveau.")
            
        if profile.best_score < 50:
            tips.append("📚 Prends le temps de bien lire les fiches de cours (Vocabulaire et Grammaire) avant les simulations.")
        elif profile.best_score < 80:
            tips.append("✍️ Revois tes erreurs fréquentes après chaque examen blanc pour cibler tes faiblesses.")
        else:
            tips.append("🚀 Excellent score ! Essaie de passer au niveau supérieur ou d'accélérer ta vitesse de lecture.")
            
        if profile.total_tests < 3:
            tips.append("⏱️ Fais au moins 3 simulations complètes pour débloquer ton analyse de compétences par le coach.")
        else:
            tips.append("🤖 Consulte tes recommandations détaillées du Coach IA dans ton espace progression.")
            
        tips.append("📅 Conseil clé : 20 minutes d'entraînement par jour valent mieux qu'une seule longue session.")

        return {
            "german_profile": profile,
            "german_level_progress": progress,
            "german_evolution_tips": tips[:3],  # Top 3 tips
            "is_german_space": is_german_space,
        }
    except Exception:
        return {
            "german_profile": None,
            "german_level_progress": 0,
            "german_evolution_tips": [],
            "is_german_space": is_german_space,
        }


def french_profile_context(request):
    """
    Injecte le profil de français (TCF) de l'utilisateur, sa progression (%),
    et des conseils d'amélioration personnalisés dans tous les templates.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "french_level": "B1",
            "french_level_progress": 0,
            "french_evolution_tips": [],
            "is_french_space": False,
        }

    path = request.path
    is_french_space = "/prep/" in path and not ("/allemand/" in path or "/allemagne/" in path or "/lebenslauf/" in path)

    try:
        from preparation_tests.models import UserExerciseProgress, CourseExercise
        
        # Progression sur les exercices de français
        total_exs = CourseExercise.objects.filter(is_active=True).count()
        completed_exs = UserExerciseProgress.objects.filter(user=request.user, is_completed=True).count()
        
        progress = 0
        if total_exs > 0:
            progress = min(max(int((completed_exs / total_exs) * 100), 0), 100)
            
        level = "B1"
        if hasattr(request.user, "profile") and request.user.profile.level:
            level = request.user.profile.level
            
        tips = []
        tips.append("🎯 Conseil clé : Le TCF Canada exige un score minimum dans les 4 compétences. Prépare-toi de façon homogène.")
        
        if completed_exs < 5:
            tips.append("✍️ Fais tes premiers exercices corrigés en Compréhension Écrite ou Orale pour lancer ton évaluation.")
        else:
            tips.append("⏱️ Teste tes conditions réelles avec un examen blanc officiel TCF.")
            
        tips.append("🤖 Discute avec le Coach IA pour recevoir des conseils et des corrections personnalisés sur l'Expression Écrite.")
        tips.append("📅 Conseil clé : 20 minutes d'entraînement par jour valent mieux qu'une seule longue session.")

        return {
            "french_level": level,
            "french_level_progress": progress,
            "french_evolution_tips": tips[:3],  # Top 3 tips
            "is_french_space": is_french_space,
        }
    except Exception:
        return {
            "french_level": "B1",
            "french_level_progress": 0,
            "french_evolution_tips": [],
            "is_french_space": is_french_space,
        }

