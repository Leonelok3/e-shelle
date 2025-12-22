from core.constants import LEVEL_PASS_THRESHOLD
from core.utils import get_next_level

def try_unlock_next_level(user, exam_code, score_percent):
    profile = getattr(user, "profile", None)
    if not profile:
        return False

    current_level = profile.level
    required_score = LEVEL_PASS_THRESHOLD.get(current_level)

    if required_score is None:
        return False

    if score_percent >= required_score:
        next_level = get_next_level(current_level)
        if next_level:
            profile.level = next_level
            profile.save()
            return True

    return False
