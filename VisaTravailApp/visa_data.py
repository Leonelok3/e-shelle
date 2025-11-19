from dataclasses import dataclass
from typing import List, Dict
from .models import UserProfile

# ============================================================
#  ORDRE DES NIVEAUX — pour comparer automatiquement
# ============================================================
LANG_LEVEL_ORDER = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}

EDU_LEVEL_ORDER = {
    "LT_BAC": 1,
    "BAC": 2,
    "BAC_PLUS_2_3": 3,
    "MASTER": 4,
    "DOCTORAT": 5,
}

# ============================================================
#  STRUCTURE PROFESSIONNELLE DES OPTIONS DE VISA
# ============================================================
@dataclass
class VisaOptionData:
    id: str
    pays: str
    nom_programme: str
    profil_cible: str
    conditions_principales: List[str]
    documents_cles: List[str]
    lien_officiel: str
    difficulte: str
    delai_approx: str
    min_experience: int
    min_niveau_etudes: str
    min_niveau_anglais: str


# ============================================================
#  DONNÉES DES PROGRAMMES — VERSION PREMIUM (12 PROGRAMMES)
# ============================================================
VISA_OPTIONS: List[VisaOptionData] = [

    # =========================
    # CANADA
    # =========================
    VisaOptionData(
        id="canada_travailleurs_qualifies",
        pays="Canada",
        nom_programme="Entrée Express – Travailleurs qualifiés",
        profil_cible="Travailleurs qualifiés avec études postsecondaires et expérience.",
        conditions_principales=[
            "Système de points (CRS).",
            "Études postsecondaires recommandées.",
            "≥ 1 an d’expérience professionnelle.",
            "Test de langue (IELTS) avec niveau B2 minimum.",
        ],
        documents_cles=[
            "Passeport.",
            "Évaluation des diplômes (EDE).",
            "Test IELTS.",
            "Attestations d'emploi.",
        ],
        lien_officiel="https://www.canada.ca/fr/immigration-refugies-citoyennete.html",
        difficulte="Élevé",
        delai_approx="12–24 mois",
        min_experience=1,
        min_niveau_etudes="BAC_PLUS_2_3",
        min_niveau_anglais="B2",
    ),
    VisaOptionData(
        id="canada_pnp",
        pays="Canada",
        nom_programme="Programme des candidats des provinces (PNP)",
        profil_cible="Personnes ciblant une province spécifique avec un métier en demande.",
        conditions_principales=[
            "Métier en demande dans la province ciblée.",
            "Charge d’expérience variable (1–3 ans).",
            "Bon niveau d’anglais (B1 ou B2).",
        ],
        documents_cles=[
            "Passeport.",
            "Test de langue.",
            "Diplômes + EDE.",
        ],
        lien_officiel="https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/candidats-des-provinces.html",
        difficulte="Moyen",
        delai_approx="6–18 mois",
        min_experience=1,
        min_niveau_etudes="BAC",
        min_niveau_anglais="B1",
    ),

    # =========================
    # ALLEMAGNE
    # =========================
    VisaOptionData(
        id="allemagne_travail_qualifie",
        pays="Allemagne",
        nom_programme="Visa travail qualifié – Allemagne",
        profil_cible="Professionnels qualifiés avec diplôme reconnu.",
        conditions_principales=[
            "Diplôme reconnu via Anabin.",
            "Souvent besoin d’un contrat.",
            "Allemand B1 recommandé.",
        ],
        documents_cles=[
            "Passeport.",
            "Contrat de travail.",
            "Reconnaissance du diplôme (Anabin).",
        ],
        lien_officiel="https://www.make-it-in-germany.com/fr/",
        difficulte="Moyen",
        delai_approx="6–12 mois",
        min_experience=1,
        min_niveau_etudes="BAC_PLUS_2_3",
        min_niveau_anglais="B1",
    ),

    # =========================
    # FRANCE
    # =========================
    VisaOptionData(
        id="france_talent",
        pays="France",
        nom_programme="Passeport Talent – Travailleur qualifié",
        profil_cible="Cadres ou travailleurs hautement qualifiés.",
        conditions_principales=[
            "Contrat de travail avec salaire minimum.",
            "Diplôme niveau Master ou expérience élevée.",
        ],
        documents_cles=[
            "Contrat de travail.",
            "Diplômes.",
            "Attestations d’expérience.",
        ],
        lien_officiel="https://www.service-public.fr/particuliers/vosdroits/F16922",
        difficulte="Moyen",
        delai_approx="6–12 mois",
        min_experience=3,
        min_niveau_etudes="MASTER",
        min_niveau_anglais="B1",
    ),

    # =========================
    # ROYAUME-UNI
    # =========================
    VisaOptionData(
        id="uk_skilled_worker",
        pays="Royaume-Uni",
        nom_programme="Skilled Worker Visa",
        profil_cible="Professionnels qualifiés avec sponsor UK.",
        conditions_principales=[
            "Offre d'un sponsor.",
            "Anglais B1 minimum.",
            "Salaire conforme au seuil.",
        ],
        documents_cles=[
            "Certificate of Sponsorship.",
            "Passeport.",
            "Attestations d’expérience.",
        ],
        lien_officiel="https://www.gov.uk/skilled-worker-visa",
        difficulte="Élevé",
        delai_approx="6–12 mois",
        min_experience=1,
        min_niveau_etudes="BAC",
        min_niveau_anglais="B1",
    ),

    # =========================
    # BELGIQUE
    # =========================
    VisaOptionData(
        id="belgique_travail_temporaire",
        pays="Belgique",
        nom_programme="Permis de travail – Belgique",
        profil_cible="Travailleurs ayant une offre d'emploi en Belgique.",
        conditions_principales=[
            "Contrat de travail.",
            "Reconnaissance parfois nécessaire.",
        ],
        documents_cles=[
            "Contrat.",
            "Passeport.",
            "Diplômes.",
        ],
        lien_officiel="https://www.migration.be/fr/travailler-en-belgique",
        difficulte="Moyen",
        delai_approx="6–12 mois",
        min_experience=1,
        min_niveau_etudes="BAC",
        min_niveau_anglais="B1",
    ),

    # =========================
    # STRATÉGIE ÉTUDES → TRAVAIL
    # =========================
    VisaOptionData(
        id="strategie_etudes_travail",
        pays="Divers",
        nom_programme="Stratégie Études → Travail",
        profil_cible="Candidats souhaitant immigrer via les études.",
        conditions_principales=[
            "Admission dans une école.",
            "Budget suffisant.",
        ],
        documents_cles=[
            "Lettre d’admission.",
            "Preuves de fonds.",
        ],
        lien_officiel="https://www.example.com/etudes-travail",
        difficulte="Variable",
        delai_approx="12–36 mois",
        min_experience=0,
        min_niveau_etudes="BAC",
        min_niveau_anglais="B1",
    ),
]


# ============================================================
#  FONCTIONS UTILITAIRES PREMIUM
# ============================================================
def _level_ok(actual: str, required: str, mapping: Dict[str, int]) -> bool:
    return mapping.get(actual, 0) >= mapping.get(required, 0)


def _score_option(profile: UserProfile, option: VisaOptionData) -> int:
    """
    Score professionnel pour trier les options :
    - Expérience
    - Niveau d’études
    - Langue
    - Correspondance pays
    """
    score = 0

    # Pays
    if option.pays in profile.pays_cibles:
        score += 20
    elif option.pays == "Divers":
        score += 5

    # Langue
    try:
        score += LANG_LEVEL_ORDER.get(profile.niveau_anglais, 0) * 2
    except:
        pass

    # Études
    score += EDU_LEVEL_ORDER.get(profile.niveau_etudes, 0) * 2

    # Expérience
    score += min(profile.annees_experience, 10) * 1.5

    return int(score)


# ============================================================
#  FONCTION PRINCIPALE : moteur de recommandation premium
# ============================================================
def recommend_visa_options(profile: UserProfile) -> List[Dict]:
    pays_cibles_list = [p.strip() for p in profile.pays_cibles.split(",") if p.strip()]

    results = []

    for option in VISA_OPTIONS:

        # Pays ciblé ou programme "Divers"
        if option.pays not in pays_cibles_list and option.pays != "Divers":
            continue

        # Expérience
        if profile.annees_experience < option.min_experience:
            continue

        # Études
        if not _level_ok(profile.niveau_etudes, option.min_niveau_etudes, EDU_LEVEL_ORDER):
            continue

        # Langue
        if not _level_ok(profile.niveau_anglais, option.min_niveau_anglais, LANG_LEVEL_ORDER):
            continue

        # Score
        score = _score_option(profile, option)

        results.append(
            {
                "id": option.id,
                "pays": option.pays,
                "nom_programme": option.nom_programme,
                "profil_cible": option.profil_cible,
                "conditions_principales": option.conditions_principales,
                "documents_cles": option.documents_cles,
                "lien_officiel": option.lien_officiel,
                "difficulte": option.difficulte,
                "delai_approx": option.delai_approx,
                "score": score,
            }
        )

    # Tri des résultats par score décroissant (meilleure pertinence)
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # Si aucun résultat strict → proposer stratégie études/travail
    if not results:
        fallback = next(
            (opt for opt in VISA_OPTIONS if opt.id == "strategie_etudes_travail"),
            None,
        )
        if fallback:
            results.append(
                {
                    "id": fallback.id,
                    "pays": fallback.pays,
                    "nom_programme": fallback.nom_programme,
                    "profil_cible": fallback.profil_cible,
                    "conditions_principales": fallback.conditions_principales,
                    "documents_cles": fallback.documents_cles,
                    "lien_officiel": fallback.lien_officiel,
                    "difficulte": fallback.difficulte,
                    "delai_approx": fallback.delai_approx,
                    "score": 0,
                }
            )

    return results
