from core.constants import LEVEL_ORDER
from profiles.models import Profile

def try_unlock_next_level(user, exam_code, score_percent):
    """
    Débloque automatiquement le niveau CECRL supérieur
    après un test blanc réussi
    """

    if score_percent < 70:
        return {
            "unlocked": False,
            "reason": "score_insufficient",
        }

    profile = getattr(user, "profile", None)
    if not profile or not profile.level:
        return {
            "unlocked": False,
            "reason": "no_profile",
        }

    levels = list(LEVEL_ORDER.keys())
    current_level = profile.level

    try:
        idx = levels.index(current_level)
    except ValueError:
        return {
            "unlocked": False,
            "reason": "invalid_level",
        }

    if idx >= len(levels) - 1:
        return {
            "unlocked": False,
            "reason": "max_level",
        }

    next_level = levels[idx + 1]

    # 🔓 Mise à jour du profil
    profile.level = next_level
    profile.save(update_fields=["level"])

    return {
        "unlocked": True,
        "old_level": current_level,
        "new_level": next_level,
    }
