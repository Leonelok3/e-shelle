"""
Service de Device Fingerprinting et Device Binding.
Assure qu'un code d'accès n'est utilisé que sur UN seul appareil.
"""
import hashlib
import logging
from django.db import transaction, IntegrityError
from django.utils import timezone

logger = logging.getLogger('edu_platform')


class DeviceConflictException(Exception):
    """Levée quand un code est déjà lié à un autre appareil."""
    pass


class SubscriptionExpiredException(Exception):
    """Levée quand l'abonnement est expiré."""
    pass


def extract_fingerprint(request) -> str:
    """
    Extrait et calcule le fingerprint composite depuis la requête.
    Le fingerprint JS est transmis via le header X-Device-Fingerprint
    ou le cookie edu_device_fp.

    Côté serveur on ajoute le subnet IP (/24) pour renforcer l'unicité.
    """
    # Fingerprint calculé côté JS (device_fingerprint.js) et transmis dans le header
    js_fingerprint = (
        request.META.get('HTTP_X_DEVICE_FINGERPRINT') or
        request.COOKIES.get('edu_device_fp') or
        ''
    )

    if not js_fingerprint:
        # Fallback : fingerprint basé sur User-Agent + IP subnet
        ip = _get_client_ip(request)
        subnet = '.'.join(ip.split('.')[:3]) if '.' in ip else ip
        ua = request.META.get('HTTP_USER_AGENT', '')
        raw = f"{ua}|{subnet}"
        js_fingerprint = hashlib.sha256(raw.encode()).hexdigest()

    # On s'assure que la valeur est bien un hash SHA256 (64 chars hex)
    if len(js_fingerprint) != 64 or not all(c in '0123456789abcdef' for c in js_fingerprint.lower()):
        # Re-hash pour normaliser
        js_fingerprint = hashlib.sha256(js_fingerprint.encode()).hexdigest()

    return js_fingerprint


def _get_client_ip(request) -> str:
    """Retourne l'adresse IP réelle du client (en tenant compte des proxies)."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _guess_device_label(request) -> str:
    """Déduit un label lisible depuis le User-Agent."""
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'iphone' in ua:
        return 'iPhone'
    if 'ipad' in ua:
        return 'iPad'
    if 'android' in ua and 'mobile' in ua:
        return 'Android Mobile'
    if 'android' in ua:
        return 'Android Tablet'
    if 'windows' in ua:
        return 'Windows PC'
    if 'mac' in ua:
        return 'Mac'
    if 'linux' in ua:
        return 'Linux'
    return 'Appareil inconnu'


def bind_device(user, access_code, request) -> 'DeviceBinding':
    """
    Lie un appareil à un code d'accès lors de la PREMIÈRE utilisation.

    1. Extrait le fingerprint depuis la requête (header JS + IP subnet)
    2. Vérifie que activation_count < max_activations (via select_for_update)
    3. Si déjà bindé à un autre appareil → lève DeviceConflictException
    4. Sinon → crée DeviceBinding et incrémente activation_count
    5. Met à jour access_code.status = 'active' et activated_at

    Args:
        user: Utilisateur authentifié.
        access_code: Instance AccessCode à activer.
        request: HttpRequest contenant les infos d'appareil.

    Returns:
        DeviceBinding créé.

    Raises:
        DeviceConflictException: Code déjà utilisé sur un autre appareil.
        ValueError: Code non activable (déjà utilisé ou révoqué).
    """
    from edu_platform.models import DeviceBinding, AccessCode as AC
    from django.utils import timezone

    fingerprint = extract_fingerprint(request)
    ip = _get_client_ip(request)
    label = _guess_device_label(request)

    with transaction.atomic():
        # Verrou pour éviter les activations concurrentes
        code = AC.objects.select_for_update().get(pk=access_code.pk)

        if code.activation_count >= code.max_activations:
            # Vérifier si c'est le MÊME appareil qui re-tente
            existing = DeviceBinding.objects.filter(
                access_code=code,
                device_fingerprint=fingerprint
            ).first()
            if existing:
                existing.increment_connection()
                return existing
            raise DeviceConflictException(
                "Ce code d'accès est déjà utilisé sur un autre appareil. "
                "Contactez le support si vous avez changé d'appareil."
            )

        if code.status == 'revoked':
            raise ValueError("Ce code d'accès a été révoqué.")

        # Création du binding
        try:
            binding, created = DeviceBinding.objects.get_or_create(
                access_code=code,
                device_fingerprint=fingerprint,
                defaults={
                    'user': user,
                    'device_label': label,
                    'ip_address': ip,
                    'is_primary': True,
                }
            )
        except IntegrityError:
            raise DeviceConflictException("Conflit d'appareil détecté.")

        if not created:
            binding.increment_connection()
        else:
            # Première activation : mettre à jour le code
            from django.utils import timezone
            code.activation_count += 1
            code.status = 'active'
            code.activated_at = timezone.now()
            code.activated_by = user
            # Calculer la date d'expiration
            from datetime import timedelta
            code.expires_at = timezone.now() + timedelta(days=code.plan.duration_days)
            code.save(update_fields=[
                'activation_count', 'status', 'activated_at',
                'activated_by', 'expires_at'
            ])
            logger.info(
                'Code %s activé par %s sur appareil %s',
                code.code, user.username, label
            )

    return binding


def verify_device(user, access_code, request) -> bool:
    """
    Vérifie que l'appareil actuel correspond à celui enregistré pour ce code.
    Appelé à CHAQUE connexion par le middleware DeviceLockMiddleware.

    Args:
        user: Utilisateur authentifié.
        access_code: Instance AccessCode active.
        request: HttpRequest en cours.

    Returns:
        True si l'appareil est autorisé.
        False si le fingerprint ne correspond pas.
    """
    from edu_platform.models import DeviceBinding

    current_fingerprint = extract_fingerprint(request)

    binding = DeviceBinding.objects.filter(
        access_code=access_code,
        user=user,
        is_primary=True
    ).first()

    if not binding:
        # Aucun binding → première utilisation → on bind
        return True  # Le middleware laissera passer, bind_device sera appelé

    if binding.device_fingerprint == current_fingerprint:
        binding.increment_connection()
        return True

    logger.warning(
        'ALERTE SÉCURITÉ: Fingerprint différent pour user %s, code %s. '
        'Enregistré: %s..., Actuel: %s...',
        user.username, access_code.code,
        binding.device_fingerprint[:12], current_fingerprint[:12]
    )
    return False
