from .coach_co import AICoachCO
from .coach_ce import AICoachCE
from .coach_ee import AICoachEE
from .coach_eo import AICoachEO

COACH_BY_SECTION = {
    "co": AICoachCO,
    "ce": AICoachCE,
    "ee": AICoachEE,
    "eo": AICoachEO,
}


def get_ai_coach(section_code):
    if not section_code:
        return None
    return COACH_BY_SECTION.get(section_code.lower())

from .coach_global import AICoachGlobal