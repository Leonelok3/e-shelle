# preparation_tests/services/levels.py

from django.db import transaction
from django.conf import settings

from core.constants import LEVEL_ORDER
from profiles.models import Profile


def try_unlock_next_level(*, user, exam_code, score_percent):
    """
    Tente de débloquer le niveau CECR suivant après un test blanc.

    Règle :
    - score >= 80% → niveau suivant débloqué
    """

    if score_percent < 80:
        return {
            "unlocked": False,
            "reason": "score_too_low",
        }

    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return {
            "unlocked": False,
            "reason": "no_profile",
        }

    current_level = profile.level

    # ordre des niveaux
    levels = list(LEVEL_ORDER.keys())

    try:
        idx = levels.index(current_level)
    except ValueError:
        return {
            "unlocked": False,
            "reason": "invalid_level",
        }

    # déjà au max
    if idx >= len(levels) - 1:
        return {
            "unlocked": False,
            "reason": "already_max",
        }

    new_level = levels[idx + 1]

    # 🔒 transaction sécurisée
    with transaction.atomic():
        profile.level = new_level
        profile.save(update_fields=["level"])

    return {
        "unlocked": True,
        "old_level": current_level,
        "new_level": new_level,
        "reason": "success",
    }
