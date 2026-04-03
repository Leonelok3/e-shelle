"""
Middleware de verrouillage appareil pour l'espace EduCam Pro.
S'applique uniquement aux URLs /edu/ pour les utilisateurs authentifiés.
"""
import logging
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

logger = logging.getLogger('edu_platform')

# Chemins exemptés de la vérification d'appareil
EXEMPT_PATHS = [
    '/edu/login/',
    '/edu/register/',
    '/edu/logout/',
    '/edu/plans/',
    '/edu/activate/',
    '/edu/device-blocked/',
]
# Chemins avec préfixe (tous les sous-chemins sont exemptés)
EXEMPT_PREFIXES = [
    '/edu/payment/',
    '/edu/webhooks/',
    '/edu/admin/',   # Back-office admin : pas de vérification abonnement
    '/edu/subscription/',
    '/edu/renew/',
    '/edu/profile/',
]
# Chemins exacts exemptés (landing page)
EXEMPT_EXACT = [
    '/edu/',
]


class DeviceLockMiddleware:
    """
    Vérifie à chaque requête vers /edu/ que :
    1. L'utilisateur a un abonnement actif
    2. L'appareil actuel est celui enregistré pour son code d'accès

    Si l'abonnement est expiré → redirect vers page de renouvellement.
    Si l'appareil est différent → redirect vers page d'erreur sécurité.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # S'applique UNIQUEMENT aux URLs /edu/
        if not request.path.startswith('/edu/'):
            return self.get_response(request)

        # Ignorer si non authentifié
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Ignorer les chemins exemptés
        if self._is_exempt(request.path):
            return self.get_response(request)

        # Vérification abonnement + appareil
        result = self._check_subscription_and_device(request)
        if result is not None:
            return result

        return self.get_response(request)

    def _is_exempt(self, path: str) -> bool:
        """Vérifie si le chemin est exempté de la vérification."""
        # Correspondance exacte
        if path in EXEMPT_EXACT:
            return True
        # Chemins exacts ou avec query string
        for exempt in EXEMPT_PATHS:
            if path == exempt or path.startswith(exempt + '?'):
                return True
        # Préfixes (sous-chemins exemptés)
        for prefix in EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    def _check_subscription_and_device(self, request):
        """
        Retourne un redirect si problème, None si tout est OK.
        """
        from edu_platform.models import AccessCode
        from edu_platform.services.device_service import verify_device, bind_device, DeviceConflictException

        user = request.user

        # Vérifier l'abonnement actif
        active_code = AccessCode.objects.filter(
            activated_by=user,
            status='active',
        ).select_related('plan').first()

        if not active_code:
            # Pas d'abonnement actif → redirect vers plans
            try:
                return redirect(reverse('edu:plans'))
            except NoReverseMatch:
                return redirect('/edu/plans/')

        # Vérifier si l'abonnement n'est pas expiré
        if active_code.is_expired:
            active_code.mark_expired()
            try:
                return redirect(reverse('edu:renew'))
            except NoReverseMatch:
                return redirect('/edu/renew/')

        # Vérifier l'appareil
        device_ok = verify_device(user, active_code, request)

        if not device_ok:
            logger.warning(
                'Accès bloqué: appareil non autorisé pour user %s',
                user.username
            )
            # Stocker info dans session pour afficher message
            request.session['edu_device_blocked'] = True
            try:
                return redirect(reverse('edu:device_blocked'))
            except NoReverseMatch:
                return redirect('/edu/device-blocked/')

        # Stocker le code actif en session pour éviter de requêter à chaque vue
        request.session['edu_active_code_id'] = active_code.pk

        return None  # Tout est OK
