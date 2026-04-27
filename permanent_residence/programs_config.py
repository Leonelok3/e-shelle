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


# ─────────────────────────────────────────────────────────────────────────────
# CONTENU DÉTAILLÉ PAR PROGRAMME (Canada uniquement)
# Sources : canada.ca / ircc.canada.ca (officiel)
# ─────────────────────────────────────────────────────────────────────────────

CANADA_PROGRAM_DETAILS: dict = {

    "entree-express-fsw": {
        "name": "Travailleurs qualifiés fédéraux (FSW)",
        "badge": "Entrée Express",
        "badge_class": "ee",
        "flag": "🇨🇦",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/admissibilite/travailleurs-qualifies-federaux.html",
        "ircc_url": "https://www.ircc.canada.ca/francais/immigrer/qualifies/index.asp",
        "short_desc": "La voie principale pour les travailleurs qualifiés n'ayant pas d'expérience canadienne. Basée sur le système Entrée Express et le score CRS.",
        "overview": "Le Programme des travailleurs qualifiés (fédéral) sélectionne des immigrants permanents en fonction de leur capacité à s'établir économiquement au Canada. Il fait partie du système Entrée Express depuis 2015.",
        "who_for": "Travailleurs qualifiés avec au moins 1 an d'expérience dans une profession qualifiée (CNP TEER 0, 1, 2 ou 3), un niveau de langue suffisant et un diplôme postsecondaire.",
        "criteria": [
            {"label": "Expérience de travail", "value": "≥ 1 an continu dans les 10 dernières années (TEER 0, 1, 2 ou 3)", "required": True},
            {"label": "Niveau de langue", "value": "CLB 7 minimum dans toutes les habiletés (FR ou EN)", "required": True},
            {"label": "Niveau d'études", "value": "Diplôme canadien ou EDE pour diplôme étranger", "required": True},
            {"label": "Score minimum", "value": "67 points sur 100 (système de points FSW)", "required": True},
            {"label": "Fonds suffisants", "value": "Selon la taille de la famille (ex : 13 757 CAD seul)", "required": True},
            {"label": "Offre d'emploi", "value": "Non obligatoire mais augmente le score CRS de +50/200 pts", "required": False},
        ],
        "fsw_points": [
            {"factor": "Compétences linguistiques", "max": 28},
            {"factor": "Niveau d'études", "max": 25},
            {"factor": "Expérience professionnelle", "max": 15},
            {"factor": "Âge", "max": 12},
            {"factor": "Offre d'emploi au Canada", "max": 10},
            {"factor": "Adaptabilité", "max": 10},
        ],
        "steps": [
            {"num": 1, "title": "Passer le test de langue", "desc": "TEF Canada ou TCF Canada (français) ou IELTS General / CELPIP (anglais). CLB 7 minimum requis dans toutes les habiletés.", "delay": "2–3 mois"},
            {"num": 2, "title": "Faire évaluer son diplôme (EDE/WES)", "desc": "Si votre diplôme est étranger, obtenez une Évaluation des diplômes étrangers (EDE) auprès de WES, IQAS ou un organisme reconnu.", "delay": "2–4 mois"},
            {"num": 3, "title": "Calculer son score et créer un profil Entrée Express", "desc": "Sur ircc.canada.ca, créez votre profil Entrée Express. Le système calcule votre score CRS automatiquement.", "delay": "1 semaine"},
            {"num": 4, "title": "Attendre une Invitation à présenter une demande (IRP)", "desc": "IRCC organise des tirages toutes les 2 semaines. Les candidats avec les scores les plus élevés reçoivent une IRP. Tirages ciblés francophones disponibles.", "delay": "Variable"},
            {"num": 5, "title": "Soumettre la demande de RP", "desc": "Dès réception de l'IRP, vous avez 60 jours pour soumettre une demande complète de résidence permanente.", "delay": "60 jours"},
            {"num": 6, "title": "Examen médical et vérification des antécédents", "desc": "Examen médical auprès d'un médecin désigné + certificat de police de chaque pays de résidence (18 ans et +).", "delay": "1–2 mois"},
            {"num": 7, "title": "Décision et confirmation RP", "desc": "IRCC traite la demande. Si approuvée, vous recevez la lettre de confirmation de résidence permanente (CDRP).", "delay": "6–12 mois"},
        ],
        "documents": [
            "Passeport valide (tous les membres de la famille)",
            "Résultats de test de langue (moins de 2 ans)",
            "Évaluation des diplômes étrangers (EDE)",
            "Relevés d'emploi détaillés (formulaire IMM 5562)",
            "Preuve de fonds suffisants (relevés bancaires)",
            "Acte de naissance (demandeur + accompagnateurs)",
            "Acte de mariage (si applicable)",
            "Examen médical (médecin désigné)",
            "Certificat de police (pays de résidence)",
            "Photos réglementaires (format IRCC)",
        ],
        "funds_table": [
            {"size": "1 personne", "amount": "13 757 CAD"},
            {"size": "2 personnes", "amount": "17 127 CAD"},
            {"size": "3 personnes", "amount": "21 055 CAD"},
            {"size": "4 personnes", "amount": "25 564 CAD"},
            {"size": "5 personnes", "amount": "28 994 CAD"},
        ],
        "tips": [
            "Visez CLB 9+ dans toutes les habiletés pour maximiser vos points CRS de langue.",
            "Si vous parlez français ET anglais (CLB 5+ en anglais), vous obtenez des points bonus pour la 2e langue officielle.",
            "Une offre d'emploi valide d'un employeur canadien (EIMT ou exempté) ajoute +50 ou +200 points CRS.",
            "Une nomination provinciale (PNP) ajoute +600 points — quasi-certitude d'obtenir une IRP.",
            "Les tirages ciblés pour francophones offrent des seuils CRS plus bas (~360–430).",
        ],
        "crs_cutoff": "~490–540 (tirages généraux) / ~360–430 (francophones)",
        "processing_time": "6–12 mois après IRP",
        "fees": "1 365 CAD (traitement) + 515 CAD (droit RP) par adulte",
        "related": ["entree-express-cec", "pnp-general", "francophones-hors-quebec"],
    },

    "entree-express-cec": {
        "name": "Expérience canadienne (CEC)",
        "badge": "Entrée Express",
        "badge_class": "ee",
        "flag": "🇨🇦",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/admissibilite/experience-canadienne.html",
        "ircc_url": "https://www.ircc.canada.ca/francais/immigrer/qualifies/index.asp",
        "short_desc": "Pour les travailleurs temporaires et diplômés étrangers qui ont déjà de l'expérience de travail au Canada.",
        "overview": "La Catégorie de l'expérience canadienne (CEC) permet aux travailleurs temporaires et diplômés étrangers au Canada de demander la résidence permanente en valorisant leur expérience acquise au Canada. Les scores CRS requis sont généralement plus bas que pour le FSW.",
        "who_for": "Travailleurs ayant au moins 1 an d'expérience qualifiée au Canada dans les 3 dernières années, avec un permis de travail valide ou un diplôme canadien. Les étudiants étrangers diplômés au Canada peuvent également y être admissibles après 1 an d'expérience.",
        "criteria": [
            {"label": "Expérience au Canada", "value": "≥ 1 an (12 mois) dans les 3 dernières années (TEER 0, 1, 2 ou 3)", "required": True},
            {"label": "Niveau de langue", "value": "CLB 7 (TEER 0/1) ou CLB 5 (TEER 2/3) minimum", "required": True},
            {"label": "Résidence au Canada", "value": "Admissible si au Canada avec statut légal (permis travail/étude)", "required": False},
            {"label": "Diplôme canadien", "value": "Valorisé mais non obligatoire si expérience de travail suffisante", "required": False},
            {"label": "Offre d'emploi", "value": "Non requise mais fortement valorisée (+200 pts CRS)", "required": False},
        ],
        "steps": [
            {"num": 1, "title": "Vérifier son éligibilité CEC", "desc": "Confirmer l'expérience au Canada (≥12 mois TEER 0/1/2/3) et le niveau de langue requis selon son CNP.", "delay": "1 semaine"},
            {"num": 2, "title": "Passer le test de langue si nécessaire", "desc": "TEF Canada / TCF Canada ou IELTS General / CELPIP. CLB 7 (TEER 0/1) ou CLB 5 (TEER 2/3).", "delay": "1–2 mois"},
            {"num": 3, "title": "Créer son profil Entrée Express", "desc": "Profil en ligne sur ircc.canada.ca avec sélection de la catégorie CEC. Score CRS calculé automatiquement.", "delay": "1 semaine"},
            {"num": 4, "title": "Recevoir l'Invitation à présenter une demande (IRP)", "desc": "Tirages CEC réguliers avec seuils souvent plus bas que FSW. Bonne nouvelle pour les travailleurs déjà au Canada.", "delay": "Variable"},
            {"num": 5, "title": "Soumettre la demande complète", "desc": "60 jours pour soumettre après réception de l'IRP. Documents similaires au FSW + preuves d'expérience canadienne.", "delay": "60 jours"},
            {"num": 6, "title": "Décision et obtention de la RP", "desc": "Traitement généralement plus rapide pour le CEC (engagement IRCC : 80% des demandes en 6 mois).", "delay": "4–8 mois"},
        ],
        "documents": [
            "Passeport valide",
            "Permis de travail ou d'études canadien actuel",
            "Lettre d'employeur canadien (durée, titre, heures, salaire)",
            "Fiches de paie / relevés d'emploi",
            "Résultats de test de langue (moins de 2 ans)",
            "T4 / avis de cotisation CRA (preuve travail au Canada)",
            "Diplômes (EDE non requis si diplôme canadien)",
            "Examen médical + certificat de police",
            "Photos réglementaires",
        ],
        "tips": [
            "Avantage clé : pas d'EDE (Évaluation des diplômes étrangers) requise si vous avez un diplôme canadien.",
            "L'expérience hors Canada et l'expérience canadienne se combinent pour augmenter votre score CRS.",
            "Si vous avez un permis de travail post-diplôme (PGWP) au Canada, vous êtes très bien positionné.",
            "Continuez à travailler au Canada pendant le traitement de votre demande — votre statut est protégé.",
        ],
        "crs_cutoff": "~450–490 (tirages généraux CEC)",
        "processing_time": "4–8 mois après IRP",
        "fees": "1 365 CAD (traitement) + 515 CAD (droit RP) par adulte",
        "related": ["entree-express-fsw", "pnp-general"],
    },

    "entree-express-fst": {
        "name": "Travailleurs de métiers spécialisés (FST)",
        "badge": "Entrée Express",
        "badge_class": "ee",
        "flag": "🇨🇦",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/admissibilite/travailleurs-metiers-specialises.html",
        "short_desc": "Pour les travailleurs qualifiés dans les métiers spécialisés : construction, électricité, plomberie, soudure, mécanique. Exige une offre d'emploi ou un certificat de compétence provinciale.",
        "overview": "Le Programme des travailleurs de métiers spécialisés (FST) s'adresse aux personnes dont l'expérience est dans les métiers de la Liste fédérale des métiers désignés. Il nécessite une offre d'emploi canadienne valide ou un certificat de compétence provinciale/territorial.",
        "who_for": "Travailleurs dans les métiers de la construction, de l'industrie, de la mécanique ou des services (CNP TEER 2 ou 3). Doit avoir une offre d'emploi à temps plein d'au moins 1 an OU un certificat de compétence délivré par une autorité canadienne.",
        "criteria": [
            {"label": "Expérience dans un métier", "value": "≥ 2 ans dans les 5 dernières années (TEER 2 ou 3 de la liste fédérale)", "required": True},
            {"label": "Niveau de langue", "value": "CLB 5 minimum (français ou anglais)", "required": True},
            {"label": "Offre d'emploi OU certificat", "value": "Offre d'emploi à temps plein ≥ 1 an OU certificat de compétence provincial", "required": True},
            {"label": "Respecter les conditions de l'offre", "value": "L'emploi doit correspondre à la CNP déclarée", "required": True},
        ],
        "steps": [
            {"num": 1, "title": "Obtenir une offre d'emploi ou un certificat", "desc": "Trouver un employeur canadien qui offre ≥ 1 an de travail dans votre métier OU obtenir un certificat de compétence provincial/territorial.", "delay": "Variable"},
            {"num": 2, "title": "Passer le test de langue", "desc": "CLB 5 minimum (moins exigeant que FSW/CEC). TEF Canada ou IELTS General.", "delay": "1–2 mois"},
            {"num": 3, "title": "Créer un profil Entrée Express", "desc": "Sélectionner la catégorie FST et entrer les détails de l'offre d'emploi ou du certificat.", "delay": "1 semaine"},
            {"num": 4, "title": "Recevoir et répondre à l'IRP", "desc": "Les tirages FST sont moins fréquents. L'offre d'emploi ou le certificat augmentent significativement le score.", "delay": "Variable"},
        ],
        "documents": [
            "Offre d'emploi validée (formulaire IRCC ou certificat d'exemption EIMT)",
            "OU Certificat de compétence provincial/territorial",
            "Preuve de 2 ans d'expérience dans le métier",
            "Résultats de test de langue",
            "Passeport valide",
            "Examen médical + certificat de police",
        ],
        "tips": [
            "Le seuil de langue CLB 5 est le plus accessible des trois voies Entrée Express.",
            "Concentrez-vous sur les provinces ayant des besoins spécifiques dans votre métier via les PNP.",
            "Certains métiers de la construction sont particulièrement recherchés en Alberta et en Ontario.",
        ],
        "crs_cutoff": "Variable selon les tirages FST ciblés",
        "processing_time": "6–12 mois après IRP",
        "fees": "1 365 CAD (traitement) + 515 CAD (droit RP) par adulte",
        "related": ["pnp-general", "entree-express-fsw"],
    },

    "pnp-general": {
        "name": "Programmes des candidats des provinces (PNP)",
        "badge": "PNP",
        "badge_class": "pnp",
        "flag": "🇨🇦",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/programmes-candidats-provinces.html",
        "short_desc": "Chaque province canadienne gère ses propres voies d'immigration selon ses besoins économiques. Une nomination PNP ajoute +600 points CRS.",
        "overview": "Les Programmes des candidats des provinces (PNP) permettent aux provinces et territoires de sélectionner des immigrants correspondant à leurs besoins économiques spécifiques. Une nomination provinciale ajoute 600 points au score CRS Entrée Express, garantissant quasi-systématiquement une Invitation à présenter une demande (IRP).",
        "who_for": "Travailleurs qualifiés, diplômés étrangers ou semi-qualifiés répondant aux besoins spécifiques d'une province. Chaque province a des flux différents : certains requièrent une offre d'emploi, d'autres visent des secteurs spécifiques ou des candidats déjà en province.",
        "provinces": [
            {"name": "Ontario (OINP)", "url": "https://www.ontario.ca/fr/page/programme-des-candidats-de-lontario", "note": "Valorise fortement les francophones et le secteur tech"},
            {"name": "Colombie-Britannique (BCPNP)", "url": "https://www.welcomebc.ca/Immigrate-to-B-C/B-C-Provincial-Nominee-Program", "note": "Tech, santé, alimentation"},
            {"name": "Alberta (AINP)", "url": "https://www.alberta.ca/ainp-overview.aspx", "note": "Énergie, construction, agriculture"},
            {"name": "Manitoba (MPNP)", "url": "https://immigratemanitoba.com/fr/", "note": "Très actif pour les francophones d'Afrique"},
            {"name": "Nouvelle-Écosse (NSNP)", "url": "https://novascotiaimmigration.com/", "note": "Petite province, délais plus courts"},
            {"name": "Saskatchewan (SINP)", "url": "https://www.saskatchewan.ca/residents/moving-to-saskatchewan", "note": "Agriculture, santé, tech"},
            {"name": "Nouveau-Brunswick (NBPNP)", "url": "https://www2.gnb.ca/content/gnb/fr/ministeres/egle/immigration.html", "note": "Francophone, très accessible"},
            {"name": "Île-du-Prince-Édouard (PEI PNP)", "url": "https://www.princeedwardisland.ca/fr/information/immigration-pei/programme-des-candidats-de-lipe", "note": "Petite province, quotas élevés"},
            {"name": "Terre-Neuve-et-Labrador (NLPNP)", "url": "https://www.gov.nl.ca/immigration/", "note": "Santé, ressources naturelles"},
        ],
        "criteria": [
            {"label": "Bonus CRS nomination", "value": "+600 points automatiques", "required": True},
            {"label": "Intention de s'établir", "value": "Dans la province nominatrice", "required": True},
            {"label": "Profil Entrée Express", "value": "Requis pour les PNP liés à Entrée Express (voie rapide)", "required": False},
            {"label": "Offre d'emploi", "value": "Souvent requise selon le flux provincial", "required": False},
        ],
        "steps": [
            {"num": 1, "title": "Identifier la province cible", "desc": "Recherchez la province dont les besoins correspondent le mieux à votre profil : secteur d'activité, niveau de langue, expérience.", "delay": "1–2 semaines"},
            {"num": 2, "title": "Soumettre une EOI (Expression of Interest) provinciale", "desc": "La plupart des provinces utilisent un système de manifestation d'intérêt en ligne. Remplissez le profil provincial et attendez une invitation.", "delay": "1–6 mois"},
            {"num": 3, "title": "Recevoir et accepter la nomination provinciale", "desc": "Si sélectionné, vous recevez une nomination. Vous avez généralement 60–90 jours pour accepter et mettre à jour votre profil Entrée Express.", "delay": "1–3 mois"},
            {"num": 4, "title": "Obtenir l'IRP fédérale (+600 pts CRS)", "desc": "Avec +600 points CRS, vous recevez quasi-systématiquement une Invitation à présenter une demande (IRP) d'IRCC.", "delay": "Quelques semaines"},
            {"num": 5, "title": "Soumettre la demande fédérale de RP", "desc": "60 jours pour soumettre la demande complète à IRCC avec tous les documents.", "delay": "60 jours"},
        ],
        "documents": [
            "Nomination provinciale officielle",
            "Profil Entrée Express mis à jour (si voie liée à EE)",
            "Passeport + résultats de langue",
            "EDE (si diplôme étranger)",
            "Preuves d'expérience de travail",
            "Offre d'emploi (si requise par la province)",
            "Examen médical + certificat de police",
        ],
        "tips": [
            "Le Manitoba et le Nouveau-Brunswick ont des flux spécifiques pour les francophones d'Afrique subsaharienne.",
            "Certains PNP (Ontario Tech, BC Tech) n'exigent pas d'offre d'emploi pour les profils tech.",
            "Vous pouvez être nominé par une province ET être dans le bassin Entrée Express en même temps.",
            "Les tirages provinciaux sont indépendants des tirages fédéraux — multipliez vos chances.",
        ],
        "crs_cutoff": "+600 pts = IRP quasi garantie",
        "processing_time": "12–18 mois (provincial + fédéral)",
        "fees": "Frais provinciaux (~250–500 CAD) + frais fédéraux (1 880 CAD/adulte)",
        "related": ["entree-express-fsw", "entree-express-cec", "quebec-pnp"],
    },

    "quebec-pnp": {
        "name": "Immigration au Québec (Arrima / PEQ)",
        "badge": "Québec",
        "badge_class": "pnp",
        "flag": "🇨🇦🏛️",
        "official_url": "https://www.quebec.ca/immigration/travailleurs-qualifies",
        "arrima_url": "https://www.immigration-quebec.gouv.qc.ca/fr/immigrer-installer/travailleurs-permanents/",
        "peq_url": "https://www.immigration-quebec.gouv.qc.ca/fr/immigrer-installer/etudiants/demeurer-quebec/programme-experience-quebecoise/",
        "short_desc": "Le Québec gère sa propre sélection d'immigrants. Le français est obligatoire. PEQ (rapide, 5 mois) ou PRTQ via Arrima pour les travailleurs qualifiés francophones.",
        "overview": "Le Québec possède un accord de coopération avec le gouvernement fédéral lui permettant de sélectionner ses propres immigrants permanents. IRCC accorde ensuite la résidence permanente aux candidats sélectionnés par le Québec. Le français est la condition principale.",
        "who_for": "Travailleurs qualifiés et diplômés francophones souhaitant s'établir au Québec. Le PEQ (Programme de l'expérience québécoise) est rapide pour ceux ayant déjà étudié ou travaillé au Québec. Le PRTQ (Programme régulier) via Arrima est ouvert aux candidats à l'étranger.",
        "programs_qc": [
            {
                "name": "PEQ — Programme de l'expérience québécoise",
                "url": "https://www.immigration-quebec.gouv.qc.ca/fr/immigrer-installer/etudiants/demeurer-quebec/programme-experience-quebecoise/",
                "desc": "Pour ceux ayant travaillé ≥ 12 mois au Québec (TEER 0/1/2/3) OU diplômé d'un établissement québécois. Traitement : ~5 mois.",
                "delay": "~5 mois",
            },
            {
                "name": "PRTQ — Programme régulier des travailleurs qualifiés",
                "url": "https://www.immigration-quebec.gouv.qc.ca/fr/immigrer-installer/travailleurs-permanents/",
                "desc": "Pour les travailleurs qualifiés à l'étranger. Sélection via Arrima (manifestation d'intérêt). Délai : 24–36 mois.",
                "delay": "24–36 mois",
            },
        ],
        "criteria": [
            {"label": "Français obligatoire", "value": "B1/B2 minimum selon le programme", "required": True},
            {"label": "PEQ : expérience au Québec", "value": "≥ 12 mois de travail qualifié OU diplôme québécois", "required": True},
            {"label": "PRTQ : diplôme et expérience", "value": "Selon la grille de sélection québécoise", "required": True},
            {"label": "Intention de s'établir au Québec", "value": "Obligatoire (déclaration)", "required": True},
        ],
        "steps": [
            {"num": 1, "title": "Choisir son programme (PEQ ou PRTQ)", "desc": "Si vous avez déjà travaillé ou étudié au Québec → PEQ (rapide). Sinon → PRTQ via Arrima.", "delay": "1 semaine"},
            {"num": 2, "title": "Déposer une Expression d'intérêt sur Arrima (PRTQ)", "desc": "Créez votre profil sur la plateforme Arrima du gouvernement du Québec. Attendez une Invitation à déposer une demande (IDD).", "delay": "Variable (6–18 mois)"},
            {"num": 3, "title": "Obtenir le Certificat de sélection du Québec (CSQ)", "desc": "Après traitement par le Québec, vous recevez le CSQ. C'est la nomination provinciale québécoise.", "delay": "12–24 mois (PRTQ) / 3–4 mois (PEQ)"},
            {"num": 4, "title": "Déposer la demande fédérale de RP", "desc": "Avec le CSQ, déposez votre demande de RP à IRCC (hors système Entrée Express pour le PRTQ).", "delay": "8–12 mois"},
        ],
        "documents": [
            "Diplôme + EDE (ou relevé de notes québécois)",
            "Résultats de test de français (TEF, TCF, DELF, DALF acceptés pour Québec)",
            "Preuves d'expérience de travail au Québec (lettres d'employeur, fiches de paie)",
            "Formulaires Arrima complétés",
            "Passeport valide",
            "Examen médical + certificat de police",
        ],
        "tips": [
            "Le DELF et le DALF sont acceptés pour le Québec — contrairement à Entrée Express fédéral.",
            "Le PEQ est l'une des voies les plus rapides au Canada (~5 mois) si vous avez déjà travaillé au Québec.",
            "Les Africains francophones sont particulièrement bien positionnés pour le PRTQ.",
            "Montréal, Québec City, Sherbrooke, Gatineau — renseignez-vous sur les régions en dehors de Montréal pour des avantages supplémentaires.",
        ],
        "crs_cutoff": "Non applicable (hors Entrée Express pour PRTQ)",
        "processing_time": "~5 mois (PEQ) / 24–36 mois (PRTQ)",
        "fees": "Frais Québec (~825 CAD) + frais fédéraux (1 880 CAD/adulte)",
        "related": ["francophones-hors-quebec", "pnp-general"],
    },

    "francophones-hors-quebec": {
        "name": "Tirages ciblés francophones (Entrée Express)",
        "badge": "Avantage francophone",
        "badge_class": "fr",
        "flag": "🇨🇦🌟",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/nouvelles/avis/2023/entree-express-invitations-nouvelles-categories.html",
        "ircc_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/entree-express/candidats/bassin-candidats.html",
        "short_desc": "Le Canada organise des tirages Entrée Express réservés aux candidats francophones hors Québec avec des seuils CRS bien inférieurs (360–430 vs 490+ général). Avantage majeur pour les candidats d'Afrique francophone.",
        "overview": "Depuis 2023, IRCC peut organiser des tirages ciblés par catégorie dans Entrée Express. Les candidats francophones (français comme 1re ou 2e langue officielle) hors Québec sont visés par ces tirages avec des seuils CRS significativement plus bas. C'est la voie la plus accessible pour les Africains francophones sans expérience canadienne.",
        "who_for": "Candidats dans le bassin Entrée Express (FSW, CEC ou FST) avec le français comme 1re ou 2e langue officielle, désireux de s'établir hors Québec (Ontario, Colombie-Britannique, Manitoba, etc.).",
        "criteria": [
            {"label": "Profil Entrée Express actif", "value": "FSW, CEC ou FST selon votre profil", "required": True},
            {"label": "Français CLB 7+", "value": "Déclaré comme 1re ou 2e langue officielle dans le profil EE", "required": True},
            {"label": "Intention hors Québec", "value": "Engagement de s'établir dans une province/territoire hors Québec", "required": True},
            {"label": "Score CRS minimum", "value": "Variable selon tirage (~360–430)", "required": True},
        ],
        "steps": [
            {"num": 1, "title": "Passer le TEF Canada ou TCF Canada (CLB 7+)", "desc": "Le français est votre atout principal. Visez CLB 9+ en compréhension orale et expression orale pour maximiser vos points.", "delay": "1–3 mois"},
            {"num": 2, "title": "Créer un profil Entrée Express et déclarer le français", "desc": "Dans votre profil IRCC, déclarez le français comme 1re ou 2e langue officielle. Entrez vos résultats TEF Canada ou TCF Canada.", "delay": "1 semaine"},
            {"num": 3, "title": "Attendre un tirage ciblé francophone", "desc": "IRCC organise des tirages spéciaux pour les francophones hors Québec. Restez informé via le site officiel IRCC.", "delay": "Variable"},
            {"num": 4, "title": "Répondre à l'IRP et soumettre la demande de RP", "desc": "Même processus que FSW/CEC après réception de l'IRP. 60 jours pour soumettre la demande complète.", "delay": "60 jours"},
        ],
        "documents": [
            "Résultats TEF Canada ou TCF Canada (CLB 7+ minimum)",
            "Profil Entrée Express actif avec français déclaré",
            "Tous documents FSW ou CEC selon votre programme de base",
            "Lettre d'intention d'établissement hors Québec",
        ],
        "tips": [
            "C'est la voie la PLUS ACCESSIBLE pour les Africains francophones sans expérience canadienne.",
            "Visez CLB 9+ en français pour maximiser vos points. Chaque niveau CLB supplémentaire ajoute des points CRS.",
            "Si vous parlez aussi anglais à CLB 5+, vous obtenez des points bonus pour la 2e langue officielle.",
            "Manitoba, Ontario (régions hors Toronto), Nouveau-Brunswick — ces provinces cherchent activement des francophones.",
            "Surveillez les tirages IRCC : https://www.canada.ca/fr/immigration-refugies-citoyennete/nouvelles/avis.html",
        ],
        "crs_cutoff": "~360–430 (bien inférieur aux tirages généraux ~490–540)",
        "processing_time": "6–12 mois après IRP",
        "fees": "1 365 CAD (traitement) + 515 CAD (droit RP) par adulte",
        "related": ["entree-express-fsw", "entree-express-cec", "quebec-pnp"],
    },

    "regroupement-familial": {
        "name": "Regroupement familial",
        "badge": "Famille",
        "badge_class": "fam",
        "flag": "🇨🇦👨‍👩‍👧",
        "official_url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada/famille/parrainer-membre-famille.html",
        "short_desc": "Les citoyens canadiens et résidents permanents peuvent parrainer certains membres de leur famille (conjoint, enfants, parents, grands-parents) pour la résidence permanente.",
        "overview": "Le Programme de parrainage familial permet aux citoyens canadiens et résidents permanents de parrainer des membres de leur famille proche pour immigrer au Canada à titre de résidents permanents. Le parrain s'engage financièrement à subvenir aux besoins de la personne parrainée.",
        "who_for": "Personnes ayant un proche qui est déjà citoyen canadien ou résident permanent (conjoint, enfant, parent, grand-parent). Aussi accessible pour les fratries dans certains cas.",
        "criteria": [
            {"label": "Parrain : citoyen ou RP canadien", "value": "≥ 18 ans, réside au Canada", "required": True},
            {"label": "Parrain : solvabilité financière", "value": "Revenu minimum selon la taille de la famille parrainée", "required": True},
            {"label": "Engagement de parrainage", "value": "3 ans (conjoint) / 10 ans (enfants) / 20 ans (parents)", "required": True},
            {"label": "Relationfamiliale prouvée", "value": "Acte de mariage, naissance, etc.", "required": True},
        ],
        "steps": [
            {"num": 1, "title": "Le parrain dépose une demande de parrainage", "desc": "Le répondant (au Canada) soumet d'abord une demande de parrainage à IRCC.", "delay": "Variable"},
            {"num": 2, "title": "La personne parrainée soumet sa demande de RP", "desc": "Simultanément ou après approbation du parrainage, la personne à l'étranger soumet sa propre demande.", "delay": "Variable"},
            {"num": 3, "title": "Traitement et décision", "desc": "IRCC traite les deux dossiers. Les délais varient significativement selon la relation familiale.", "delay": "12–48 mois"},
        ],
        "documents": [
            "Acte de mariage ou preuve d'union (conjoint)",
            "Actes de naissance (enfants)",
            "Preuves de revenus du parrain (T4, avis d'imposition)",
            "Passeport valide (parrain et personne parrainée)",
            "Examen médical + certificat de police (personne parrainée)",
            "Photos + formulaires IRCC spécifiques",
        ],
        "tips": [
            "Conjoint/partenaire : délai moyen 12–18 mois si conjoint se trouve à l'extérieur du Canada.",
            "Parents/grands-parents : soumis via la Voie d'accès pour parents et grands-parents (PGP) — quotas annuels limités.",
            "Le parrainage de conjoint est l'une des voies les plus utilisées par les candidats africains avec un partenaire déjà au Canada.",
        ],
        "crs_cutoff": "Non applicable (hors Entrée Express)",
        "processing_time": "12–48 mois selon la relation",
        "fees": "1 080 CAD (traitement conjoint) + 515 CAD (droit RP)",
        "related": ["entree-express-fsw", "pnp-general"],
    },
}


def get_program_detail(slug: str) -> dict | None:
    """Retourne le contenu détaillé d'un programme Canada par son slug."""
    return CANADA_PROGRAM_DETAILS.get(slug)
