from core.constants import LEVEL_ORDER, CEFR_BADGES

def build_cefr_badges(user):
    """
    Retourne la liste des badges CECRL
    avec état : unlocked / locked / current
    """
    profile = getattr(user, "profile", None)
    user_level = profile.level if profile else "A1"

    badges = []

    for level, meta in CEFR_BADGES.items():
        badges.append({
            "level": level,
            "label": meta["label"],
            "icon": meta["icon"],
            "color": meta["color"],
            "is_unlocked": LEVEL_ORDER[level] <= LEVEL_ORDER[user_level],
            "is_current": level == user_level,
        })

    # tri dans l’ordre CECRL
    badges.sort(key=lambda b: LEVEL_ORDER[b["level"]])

    return badges
