from core.constants import LEVEL_ORDER

def get_next_level(current_level):
    levels = list(LEVEL_ORDER.keys())
    try:
        idx = levels.index(current_level)
        return levels[idx + 1]
    except (ValueError, IndexError):
        return None
