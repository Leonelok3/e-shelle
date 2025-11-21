# permanent_residence/programs_config.py
"""
Moteur d'orientation RP (Canada + Australie) pour immigration97.

⚠️ IMPORTANT :
Les règles ci-dessous sont volontairement simplifiées.
C'est un outil d'orientation, pas une décision officielle.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from .models import PRProfile


# -----------------------------
# 1. Modèle de programme
# -----------------------------

@dataclass
class PRProgram:
    code: str
    country: str           # "CA" ou "AU"
    name: str
    category: str          # ex: "federal", "pnp", "skilled", "sponsor"
    description: str

    min_age: int | None = None
    max_age: int | None = None

    min_edu_level: str | None = None      # code de education_level
    min_french_level: str | None = None   # "b1", "b2", "c1", "c2", ...
    min_english_level: str | None = None

    requires_job_offer: bool | None = None
    requires_french: bool | None = None
    requires_english: bool | None = None


# ordre des niveaux pour comparer
EDU_ORDER = {
    "none": 0,
    "secondary": 1,
    "post_1_2": 2,
    "bachelor": 3,
    "master": 4,
    "phd": 5,
    "other": 2,
}

LANG_ORDER = {
    "none": 0,
    "a2": 1,
    "b1": 2,
    "b2": 3,
    "c1": 4,
    "c2": 5,
}


def _edu_index(code: str | None) -> int:
    return EDU_ORDER.get(code or "none", 0)


def _lang_index(code: str | None) -> int:
    return LANG_ORDER.get(code or "none", 0)


# -----------------------------
# 2. Liste des programmes
# -----------------------------

PROGRAMS: List[PRProgram] = [
    # ------ CANADA ------ #
    PRProgram(
        code="CA_EE_FSW",
        country="CA",
        name="Entrée Express – Travailleurs qualifiés (fédéral)",
        category="federal",
        description=(
            "Programme principal pour travailleurs qualifiés à l'étranger. "
            "Basé sur un système de points (CRS)."
        ),
        min_age=18,
        max_age=45,
        min_edu_level="bachelor",
        min_french_level="b2",   # simplifié
        min_english_level="b2",
        requires_french=None,
        requires_english=True,
        requires_job_offer=False,
    ),
    PRProgram(
        code="CA_EE_CEC",
        country="CA",
        name="Entrée Express – Catégorie de l’expérience canadienne (CEC)",
        category="federal",
        description=(
            "Pour les personnes ayant déjà une expérience de travail qualifiée au Canada."
        ),
        min_age=18,
        max_age=47,
        min_edu_level="post_1_2",
        min_french_level="b2",
        min_english_level="b2",
        requires_job_offer=False,
    ),
    PRProgram(
        code="CA_PNP",
        country="CA",
        name="Programmes des candidats des provinces (PNP)",
        category="pnp",
        description=(
            "Programmes provinciaux. Certains exigent une offre d'emploi ou un lien avec la province."
        ),
        min_age=18,
        max_age=49,
        min_edu_level="secondary",
        min_french_level="b1",
        min_english_level="b1",
        requires_job_offer=None,
    ),
    PRProgram(
        code="CA_MOB_FR",
        country="CA",
        name="Mobilité francophone (permis de travail)",
        category="work",
        description=(
            "Permis de travail dispensé d'EIMT pour les francophones hors Québec, "
            "souvent première étape avant la RP."
        ),
        min_age=18,
        max_age=55,
        min_edu_level="secondary",
        min_french_level="b2",
        min_english_level=None,
        requires_french=True,
        requires_job_offer=True,
    ),

    # ------ AUSTRALIE ------ #
    PRProgram(
        code="AU_SKILLED_INDEPENDENT",
        country="AU",
        name="Skilled Independent Visa (subclass 189)",
        category="skilled",
        description=(
            "Visa à points pour les travailleurs qualifiés sans sponsor spécifique. "
            "Basé sur âge, études, expérience, anglais, métier sur liste."
        ),
        min_age=18,
        max_age=45,
        min_edu_level="bachelor",
        min_english_level="b2",
        requires_english=True,
    ),
    PRProgram(
        code="AU_SKILLED_NOMINATED",
        country="AU",
        name="Skilled Nominated Visa (subclass 190)",
        category="skilled",
        description="Visa à points avec nomination par un État/territoire australien.",
        min_age=18,
        max_age=45,
        min_edu_level="bachelor",
        min_english_level="b2",
        requires_english=True,
    ),
    PRProgram(
        code="AU_SKILLED_REGIONAL",
        country="AU",
        name="Skilled Work Regional Visa (subclass 491)",
        category="skilled",
        description="Visa de travail régional à points, souvent plus accessible que le 189/190.",
        min_age=18,
        max_age=45,
        min_edu_level="secondary",
        min_english_level="b1",
        requires_english=True,
    ),
    PRProgram(
        code="AU_EMPLOYER_SPONSOR",
        country="AU",
        name="Employer Sponsored (TSS / ENS…)",
        category="sponsor",
        description="Visas sponsorisés par un employeur australien (peut mener à la RP).",
        min_age=18,
        max_age=50,
        min_edu_level="secondary",
        min_english_level="b1",
        requires_english=True,
        requires_job_offer=True,
    ),
]


# -----------------------------
# 3. Analyse d'un profil
# -----------------------------

def evaluate_profile(profile: PRProfile) -> List[Dict[str, Any]]:
    """
    Retourne une liste de dicts :
    [
      {
        "program": PRProgram,
        "eligible": bool,
        "reasons": [str, ...],     # explications / conseils
      },
      ...
    ]
    """

    results: List[Dict[str, Any]] = []

    edu = _edu_index(profile.education_level)
    fr = _lang_index(profile.french_level)
    en = _lang_index(profile.english_level or None)
    age = profile.age or 0
    exp_years = profile.years_experience or 0

    for prog in PROGRAMS:
        if prog.country != profile.country:
            continue

        eligible = True
        reasons: List[str] = []

        # Âge
        if prog.min_age is not None and age < prog.min_age:
            eligible = False
            reasons.append(f"Âge minimum conseillé : {prog.min_age} ans.")
        if prog.max_age is not None and age > prog.max_age:
            eligible = False
            reasons.append(
                f"Au-delà de {prog.max_age} ans, les points d'âge sont très faibles pour ce programme."
            )

        # Études
        if prog.min_edu_level and edu < _edu_index(prog.min_edu_level):
            eligible = False
            reasons.append("Ton niveau d'études est un peu juste pour ce programme.")

        # Français / anglais
        if prog.min_french_level:
            if fr < _lang_index(prog.min_french_level):
                eligible = False
                reasons.append(
                    f"Ton niveau de français devrait être au moins {prog.min_french_level.upper()}."
                )

        if prog.min_english_level:
            if en < _lang_index(prog.min_english_level):
                eligible = False
                reasons.append(
                    f"Ton niveau d’anglais devrait être au moins {prog.min_english_level.upper()}."
                )

        # Exigence “french speaker”
        if prog.requires_french and fr <= _lang_index("b1"):
            eligible = False
            reasons.append("Ce programme cible plutôt des profils francophones intermédiaires/avancés.")

        if prog.requires_english and en <= _lang_index("b1"):
            eligible = False
            reasons.append("Il faut un niveau d’anglais intermédiaire ou avancé pour ce visa.")

        # Offre d'emploi
        if prog.requires_job_offer and not profile.has_job_offer:
            eligible = False
            reasons.append("Une offre d'emploi validée est généralement nécessaire.")

        # Expérience (simple règle générique)
        if exp_years < 1:
            reasons.append("Moins d’un an d’expérience qualifiée – certains programmes demandent 1–2 ans.")
            # on ne met pas auto non-éligible, mais on avertit

        # Résumé
        if eligible and not reasons:
            reasons.append("Ton profil semble globalement compatible avec ce programme (à vérifier en détail).")
        elif not eligible:
            reasons.insert(0, "Profil à renforcer avant de viser ce programme.")

        results.append(
            {
                "program": prog,
                "eligible": eligible,
                "reasons": reasons,
            }
        )

    return results
