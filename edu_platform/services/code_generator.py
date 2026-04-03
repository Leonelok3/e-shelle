"""
Service de génération de codes d'accès uniques.
Format : XXXX-XXXX-XXXX-XXXX (alphanumérique majuscule)
"""
import secrets
import string
import logging
from django.db import transaction

logger = logging.getLogger('edu_platform')

# Caractères utilisés : lettres majuscules + chiffres, sans ambiguïtés (O, 0, I, l)
CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
CODE_GROUP_SIZE = 4
CODE_GROUPS = 4


def _generate_raw_code() -> str:
    """Génère un code brut de 16 caractères aléatoires sécurisés."""
    return ''.join(secrets.choice(CODE_CHARS) for _ in range(CODE_GROUP_SIZE * CODE_GROUPS))


def _format_code(raw: str) -> str:
    """Formate en groupes : XXXX-XXXX-XXXX-XXXX."""
    groups = [raw[i:i + CODE_GROUP_SIZE] for i in range(0, len(raw), CODE_GROUP_SIZE)]
    return '-'.join(groups)


def generate_access_code(transaction_obj) -> 'AccessCode':
    """
    Génère un code d'accès unique après paiement confirmé.

    1. Génère un code alphanumérique unique de 16 caractères (groupes de 4 séparés par -)
    2. Vérifie l'unicité en base (boucle avec retry x3)
    3. Crée l'objet AccessCode avec status='unused'
    4. Déclenche l'envoi par SMS et Email
    5. Retourne l'AccessCode créé

    Args:
        transaction_obj: Instance de PaymentTransaction confirmée.

    Returns:
        AccessCode nouvellement créé.

    Raises:
        RuntimeError: Si l'unicité du code ne peut être garantie après 3 tentatives.
    """
    from edu_platform.models import AccessCode
    from edu_platform.services.notification_service import send_access_code_notification

    max_retries = 3
    for attempt in range(max_retries):
        raw = _generate_raw_code()
        formatted_code = _format_code(raw)

        if not AccessCode.objects.filter(code=formatted_code).exists():
            with transaction.atomic():
                access_code = AccessCode.objects.create(
                    code=formatted_code,
                    plan=transaction_obj.plan,
                    transaction=transaction_obj,
                    status='unused',
                )
            logger.info(
                'Code d\'accès généré: %s pour transaction %s',
                formatted_code, transaction_obj.transaction_id
            )
            # Envoi asynchrone SMS + Email
            try:
                send_access_code_notification(access_code, transaction_obj.user)
            except Exception as e:
                logger.error('Erreur envoi notification code %s: %s', formatted_code, e)
            return access_code

    raise RuntimeError(
        f"Impossible de générer un code unique après {max_retries} tentatives."
    )


def generate_test_code(plan) -> 'AccessCode':
    """
    Génère un code de test sans transaction associée (dev/staging uniquement).
    À utiliser UNIQUEMENT via la commande de gestion generate_test_code.
    """
    from edu_platform.models import AccessCode
    import django.conf as conf
    if not conf.settings.DEBUG:
        raise PermissionError("Les codes de test ne sont autorisés qu'en mode DEBUG.")

    for _ in range(3):
        raw = _generate_raw_code()
        formatted_code = _format_code(raw)
        if not AccessCode.objects.filter(code=formatted_code).exists():
            return AccessCode.objects.create(
                code=formatted_code,
                plan=plan,
                status='unused',
            )
    raise RuntimeError("Impossible de générer un code de test unique.")
