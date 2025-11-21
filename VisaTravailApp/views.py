from __future__ import annotations

"""
VUES PRINCIPALES DU MODULE VisaTravailApp

Ce fichier est organisé en sections :

1) Imports & helpers généraux
2) Vues "parcours visa travail" (home, profil, résultats, plan d'action, ressources)
3) Coach & scoring (compute_offer_match, score global, vue 360°)
4) Job board manuel (offres en base + détails)
5) Tableau de bord des candidatures (JobApplication)
6) Coach CV (analyse simple + upload CV PDF/DOCX/TXT)
7) Export PDF du plan d'action
"""

# ============================================================
# 1) IMPORTS & HELPERS GÉNÉRAUX
# ============================================================

from typing import Dict, List, Tuple

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.template.loader import get_template
from django.db.models import Q

from xhtml2pdf import pisa

from .models import (
    UserProfile,
    ActionStep,
    JobOffer,
    JobApplication,
)
from .forms import (
    UserProfileForm,
    ActionStepStatusForm,
    JobApplicationForm,
    CVAnalysisForm,
)
from .visa_data import recommend_visa_options

# Imports optionnels pour l’extraction de CV
try:  # PDF
    import PyPDF2
except ImportError:  # si non installé, on gère plus bas
    PyPDF2 = None  # type: ignore

try:  # DOCX
    import docx  # python-docx
except ImportError:
    docx = None  # type: ignore


# ============================================================
# 2) VUES PARCOURS VISA TRAVAIL (HOME, PROFIL, RÉSULTATS, PLAN, RESSOURCES)
# ============================================================


def home(request):
    """
    Page d'accueil de l'app Visa Travail.
    Affiche le pitch et un bouton "Commencer le diagnostic".
    """
    return render(request, "visa_travail/home.html")


@require_http_methods(["GET", "POST"])
def profil_create(request):
    """
    Création / saisie du profil utilisateur :
    - infos de base
    - pays ciblés
    - niveau d'études, expérience, langues, budget...
    Une fois le formulaire valide, on crée le UserProfile
    puis on redirige vers la page de résultats.
    """
    if request.method == "POST":
        form = UserProfileForm(request.POST)
        if form.is_valid():
            profile = form.save()
            return redirect("visa_travail:resultats", profile_id=profile.pk)
    else:
        form = UserProfileForm()

    return render(request, "visa_travail/profil_form.html", {"form": form})


def resultats(request, profile_id: int):
    """
    Affiche les options de visa recommandées pour un profil donné.
    Utilise la logique définie dans visa_data.recommend_visa_options.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)
    options = recommend_visa_options(profile)
    return render(
        request,
        "visa_travail/resultats.html",
        {"profile": profile, "options": options},
    )


def _create_default_actions_if_needed(profile: UserProfile, options: List[Dict]) -> None:
    """
    Génère un plan d'action par défaut (ActionStep) pour un profil,
    uniquement si aucune étape n'existe encore.
    """
    if profile.actions.exists():
        return

    steps: List[ActionStep] = []
    ordre = 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Clarifier ton projet et ton pays cible",
            description="Revoir les options proposées et choisir le pays/programme prioritaire.",
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Mettre à jour ton CV au format international",
            description="Adapter ton CV au modèle du pays ciblé (mise en page, mots-clés, langue).",
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Préparer les preuves d'expérience",
            description="Rassembler attestations d'emploi, contrats, fiches de paie, lettres de recommandation.",
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Vérifier tes niveaux de langue",
            description="Planifier ou passer les tests de langue requis (IELTS, TEF, etc.).",
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Organiser tes documents officiels",
            description="Passeport, diplômes, traductions certifiées, extrait de casier judiciaire, etc.",
            ordre=ordre,
        )
    )
    ordre += 1

    programme_names = ", ".join(o["nom_programme"] for o in options)
    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Étudier en détail les programmes sélectionnés",
            description=f"Lire les conditions officielles des programmes suivants : {programme_names}.",
            ordre=ordre,
        )
    )

    ActionStep.objects.bulk_create(steps)


def _build_coach_message(
    profile: UserProfile, progress_percent: int, pays_prioritaire: str
) -> Dict[str, str]:
    """
    Génère un titre + message pour le coach en fonction :
    - de la progression globale
    - du pays prioritaire
    """
    nom_affichage = profile.nom or "ton profil"

    if progress_percent == 0:
        title = "On démarre ton projet Visa Travail 🚀"
        message = (
            f"Pour {nom_affichage}, l’objectif est de poser des bases solides : "
            f"choisir clairement le pays prioritaire (actuellement : {pays_prioritaire}), "
            "mettre à jour le CV et rassembler les premiers documents (diplômes, expérience). "
            "Commence par compléter au moins 2–3 étapes du plan pour lancer la dynamique."
        )
    elif progress_percent < 40:
        title = "Tu es en phase de lancement ✅"
        message = (
            f"Ton projet avance pour {nom_affichage}, mais il reste encore beaucoup de marge. "
            f"Concentre-toi maintenant sur la validation des étapes liées au pays {pays_prioritaire} : "
            "adaptation du CV, préparation des preuves d’expérience et premières candidatures ciblées."
        )
    elif progress_percent < 80:
        title = "Très bonne dynamique, continue 💪"
        message = (
            f"Tu as déjà réalisé une bonne partie du plan pour {nom_affichage}. "
            "C’est le bon moment pour intensifier les candidatures de qualité, suivre les réponses, "
            f"et ajuster ta stratégie pour le pays {pays_prioritaire}. "
            "Ne relâche pas : c’est souvent à ce stade que les premiers retours sérieux arrivent."
        )
    else:
        title = "Tu es proche du but 🎯"
        message = (
            f"Ton plan est presque entièrement complété pour {nom_affichage}. "
            "Assure-toi que ton dossier est propre (CV, lettres, documents officiels) et que tes candidatures "
            f"pour {pays_prioritaire} sont bien suivies (relances, rappels, mises à jour). "
            "Maintenant, c’est la régularité et le suivi qui feront la différence."
        )

    return {"title": title, "message": message}


@require_http_methods(["GET", "POST"])
def plan_action(request, profile_id: int):
    """
    Plan d'action personnalisé + mise à jour des statuts + coach IA + score global.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)
    options = recommend_visa_options(profile)

    # Génère des étapes par défaut si besoin
    _create_default_actions_if_needed(profile, options)

    # Mise à jour du statut d'une étape
    if request.method == "POST":
        step_id = request.POST.get("step_id")
        step = get_object_or_404(ActionStep, pk=step_id, user_profile=profile)
        form = ActionStepStatusForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            return redirect("visa_travail:plan_action", profile_id=profile.pk)

    steps = profile.actions.all()
    total_steps = steps.count()
    done_steps = steps.filter(statut=ActionStep.STATUT_TERMINE).count()
    progress_percent = int((done_steps / total_steps) * 100) if total_steps > 0 else 0

    # Label de progression
    if progress_percent == 0:
        progress_label = "Tu démarres ton parcours"
    elif progress_percent < 40:
        progress_label = "Tu es en phase de lancement"
    elif progress_percent < 80:
        progress_label = "Bonne progression"
    else:
        progress_label = "Tu es proche de ton objectif"

    # Pays prioritaire (premier pays coché)
    if profile.pays_cibles:
        pays_prioritaire = profile.pays_cibles.split(",")[0].strip()
    else:
        pays_prioritaire = "à définir"

    # Coach IA (titre + message)
    coach = _build_coach_message(profile, progress_percent, pays_prioritaire)
    coach_title = coach["title"]
    coach_message = coach["message"]

    # Score global (Coach Niveau 7)
    global_data = compute_global_project_score(profile)

    return render(
        request,
        "visa_travail/plan_action.html",
        {
            "profile": profile,
            "steps": steps,
            "done_steps": done_steps,
            "total_steps": total_steps,
            "progress_percent": progress_percent,
            "progress_label": progress_label,
            "coach_title": coach_title,
            "coach_message": coach_message,
            "pays_prioritaire": pays_prioritaire,
            "global": global_data,
        },
    )


def ressources(request):
    """
    Page de ressources et de prévention des arnaques.
    """
    return render(request, "visa_travail/ressources.html")


# ============================================================
# 3) COACH & SCORING (MATCH OFFRES, SCORE GLOBAL, VUE 360°)
# ============================================================


def normalize(text: str) -> str:
    """
    Normalise une chaîne pour le matching (minuscule + strip).
    """
    return (text or "").lower().strip()


def keyword_match_score(a: str, b: str) -> int:
    """
    Score simple basé sur le nombre de mots communs entre deux textes.
    Renvoie un score entre 0 et 100.
    """
    a_tokens = [t for t in normalize(a).split() if t]
    b_tokens = [t for t in normalize(b).split() if t]
    if not a_tokens or not b_tokens:
        return 0

    common = set(a_tokens) & set(b_tokens)
    if not common:
        return 0

    ratio = len(common) / len(a_tokens)
    score = int(min(ratio, 1.0) * 100)
    return score


def compute_offer_match(profile: UserProfile, offer: JobOffer) -> Dict[str, object]:
    """
    Calcule un score de compatibilité entre un profil et une offre.
    Utilisé pour le job board (Coach Niveau 6).
    """
    profil_job = profile.domaine_metier or ""
    offer_text = f"{offer.titre or ''} {offer.domaine or ''}"

    # Matching métier ↔ offre
    kw_score = keyword_match_score(profil_job, offer_text)  # 0–100

    # Matching pays
    pays_cibles_list = [
        p.strip().lower()
        for p in (profile.pays_cibles or "").split(",")
        if p.strip()
    ]
    pays_match = False
    country_bonus = 0
    if offer.pays:
        offer_country_lower = offer.pays.lower()
        for target in pays_cibles_list:
            if target in offer_country_lower or offer_country_lower in target:
                pays_match = True
                country_bonus = 25
                break

    # Score brut (60% métier, 25% pays)
    base_score = int(kw_score * 0.6) + country_bonus
    if base_score > 100:
        base_score = 100

    # Label
    if base_score >= 80:
        label = "Excellent"
    elif base_score >= 60:
        label = "Bon"
    elif base_score >= 40:
        label = "Moyen"
    else:
        label = "Faible"

    # Message
    if kw_score < 20 and not pays_match:
        reason = "Profil peu aligné sur le métier et le pays de cette offre."
    elif kw_score >= 40 and not pays_match:
        reason = "Métier relativement aligné, mais le pays ne fait pas partie de tes priorités."
    elif kw_score < 40 and pays_match:
        reason = "Pays aligné avec ton projet, mais le métier ne correspond pas parfaitement à ton profil."
    else:
        reason = "Bon alignement entre ton métier et le pays ciblé pour cette offre."

    return {
        "score": base_score,
        "label": label,
        "reason": reason,
        "kw_score": kw_score,
        "pays_match": pays_match,
    }


# Maps de scoring pour le profil
LANG_SCORE_MAP = {
    "A1": 0.2,
    "A2": 0.4,
    "B1": 0.6,
    "B2": 0.8,
    "C1": 0.9,
    "C2": 1.0,
}

EDU_SCORE_MAP = {
    "LT_BAC": 0.3,
    "BAC": 0.5,
    "BAC_PLUS_2_3": 0.7,
    "MASTER": 0.9,
    "DOCTORAT": 1.0,
}

BUDGET_SCORE_MAP = {
    "INF_1000": 0.3,
    "1000_3000": 0.7,
    "SUP_3000": 1.0,
}


def compute_profile_score(profile: UserProfile) -> Dict[str, object]:
    """
    Score 0–40 basé sur : études, expérience, langues, budget.
    """
    edu_factor = EDU_SCORE_MAP.get(profile.niveau_etudes, 0.4)

    exp_years = profile.annees_experience or 0
    exp_factor = min(exp_years / 5.0, 1.0)

    ang_factor = LANG_SCORE_MAP.get(profile.niveau_anglais, 0.4)
    pays_factor = LANG_SCORE_MAP.get(profile.niveau_langue_pays, 0.4)
    lang_factor = max(ang_factor, pays_factor)

    budget_factor = BUDGET_SCORE_MAP.get(profile.budget, 0.4)

    raw = (
        edu_factor * 0.35
        + exp_factor * 0.30
        + lang_factor * 0.20
        + budget_factor * 0.15
    )
    score = int(raw * 40)

    if score >= 32:
        level = "Profil très solide"
    elif score >= 24:
        level = "Profil correct"
    elif score >= 16:
        level = "Profil à renforcer"
    else:
        level = "Profil fragile pour un visa travail"

    return {
        "score": score,
        "level": level,
        "edu_factor": edu_factor,
        "exp_factor": exp_factor,
        "lang_factor": lang_factor,
        "budget_factor": budget_factor,
    }


def compute_matching_score(profile: UserProfile) -> Dict[str, object]:
    """
    Score 0–40 basé sur le matching moyen avec les offres JobOffer.
    """
    offers = JobOffer.objects.all()
    if not offers.exists():
        return {
            "score": 0,
            "avg_match": 0,
            "count_offers": 0,
        }

    scores: List[int] = []
    for offer in offers:
        match = compute_offer_match(profile, offer)
        scores.append(match["score"])

    avg_match = sum(scores) / len(scores) if scores else 0
    score = int((avg_match / 100.0) * 40)

    return {
        "score": score,
        "avg_match": int(avg_match),
        "count_offers": len(scores),
    }


def compute_progress_score(profile: UserProfile) -> Dict[str, object]:
    """
    Score 0–20 basé sur la progression du plan d'action (ActionStep).
    """
    steps = profile.actions.all()
    total = steps.count()
    if total == 0:
        return {
            "score": 0,
            "total": 0,
            "done": 0,
            "percent": 0,
        }

    done = steps.filter(statut=ActionStep.STATUT_TERMINE).count()
    percent = int((done / total) * 100)
    score = int((percent / 100.0) * 20)

    return {
        "score": score,
        "total": total,
        "done": done,
        "percent": percent,
    }


def compute_global_project_score(profile: UserProfile) -> Dict[str, object]:
    """
    Combine :
    - profil (0–40)
    - matching offres (0–40)
    - progression (0–20)
    → Score global 0–100 + commentaires.
    """
    profile_part = compute_profile_score(profile)
    matching_part = compute_matching_score(profile)
    progress_part = compute_progress_score(profile)

    global_score = (
        profile_part["score"] + matching_part["score"] + progress_part["score"]
    )

    if global_score >= 80:
        label = "Projet très bien positionné"
    elif global_score >= 60:
        label = "Projet bien engagé"
    elif global_score >= 40:
        label = "Projet en construction"
    else:
        label = "Projet à structurer"

    insights: List[str] = []

    # Profil
    if profile_part["score"] < 20:
        insights.append(
            "Renforce ton profil : expérience, formations complémentaires ou langues peuvent vraiment améliorer tes chances."
        )
    elif profile_part["score"] < 30:
        insights.append(
            "Ton profil est correct, mais tu peux le rendre plus compétitif en travaillant sur les langues et la spécialisation."
        )
    else:
        insights.append(
            "Ton profil est déjà solide. Mets maintenant le focus sur le ciblage des offres et la qualité des candidatures."
        )

    # Matching
    if matching_part["score"] < 16:
        insights.append(
            "Le matching avec les offres actuelles est faible : vérifie si tu cibles les bons pays et les bons métiers."
        )
    elif matching_part["score"] < 28:
        insights.append(
            "Le matching avec les offres est moyen : tu peux affiner les filtres (pays, mots-clés) et adapter ton CV aux offres."
        )
    else:
        insights.append(
            "Le matching avec les offres est bon : continue à postuler régulièrement sur les offres compatibles."
        )

    # Progression
    if progress_part["score"] < 8:
        insights.append(
            "La progression dans ton plan d’action est encore faible : fixe-toi des objectifs hebdomadaires concrets."
        )
    elif progress_part["score"] < 14:
        insights.append(
            "Tu avances, mais tu peux encore accélérer le rythme sur les étapes clés (CV, candidatures, tests de langue)."
        )
    else:
        insights.append(
            "Très bonne progression dans ton plan d’action : continue sur cette dynamique jusqu’aux premières offres concrètes."
        )

    return {
        "global_score": global_score,
        "label": label,
        "profile_part": profile_part,
        "matching_part": matching_part,
        "progress_part": progress_part,
        "insights": insights,
    }


@require_http_methods(["GET"])
def project_overview(request, profile_id: int):
    """
    Vue 360° d'un profil :
    - résumé du profil
    - options de visa
    - top offres compatibles
    - candidatures récentes
    - score global du projet
    - lien vers les différents modules
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)

    # Options de visa recommandées
    visa_options = recommend_visa_options(profile)

    # Top offres compatibles (JobOffer) avec scoring
    all_offers = JobOffer.objects.all().order_by("-date_publication")[:50]
    scored_offers: List[Tuple[int, Dict[str, object], JobOffer]] = []
    for offer in all_offers:
        match = compute_offer_match(profile, offer)
        scored_offers.append((match["score"], match, offer))

    scored_offers.sort(key=lambda x: x[0], reverse=True)
    top_offers = [
        {"score": score, "match": match, "offer": offer}
        for score, match, offer in scored_offers[:5]
    ]

    # Candidatures récentes
    recent_applications = JobApplication.objects.filter(
        user_profile=profile
    ).order_by("-date_candidature", "-id")[:10]

    # Score global du projet
    global_data = compute_global_project_score(profile)

    # Plan d'action
    steps = profile.actions.all()
    total_steps = steps.count()
    done_steps = steps.filter(statut=ActionStep.STATUT_TERMINE).count()
    progress_percent = int((done_steps / total_steps) * 100) if total_steps > 0 else 0

    context = {
        "profile": profile,
        "visa_options": visa_options,
        "top_offers": top_offers,
        "recent_applications": recent_applications,
        "global": global_data,
        "steps": steps,
        "total_steps": total_steps,
        "done_steps": done_steps,
        "progress_percent": progress_percent,
    }

    return render(request, "visa_travail/project_overview.html", context)


# ============================================================
# 4) JOB BOARD MANUEL (OFFRES EN BASE + DÉTAIL)
# ============================================================


@require_http_methods(["GET"])
def job_offers_list(request):
    """
    Job board des offres en base (JobOffer) avec filtres pays/domaine.
    Si un profile_id est passé en query (?profile=ID),
    on calcule un score de compatibilité pour chaque offre.
    """
    pays = request.GET.get("pays", "").strip()
    domaine = request.GET.get("domaine", "").strip()
    profile_id = request.GET.get("profile", "").strip()

    offers_qs = JobOffer.objects.all().order_by("-date_publication")

    if pays:
        offers_qs = offers_qs.filter(pays__icontains=pays)
    if domaine:
        offers_qs = offers_qs.filter(domaine__icontains=domaine)

    offers = list(offers_qs)

    profile = None
    if profile_id:
        try:
            profile = UserProfile.objects.get(pk=int(profile_id))
        except (UserProfile.DoesNotExist, ValueError, TypeError):
            profile = None

    # Avec profil → calcul du score de compatibilité
    if profile is not None:
        for offer in offers:
            match = compute_offer_match(profile, offer)
            offer.match_score = match["score"]
            offer.match_label = match["label"]
            offer.match_reason = match["reason"]
            offer.match_pays_ok = match["pays_match"]
        offers.sort(key=lambda o: getattr(o, "match_score", 0), reverse=True)

    context = {
        "offers": offers,
        "pays": pays,
        "domaine": domaine,
        "profile": profile,
    }
    return render(request, "visa_travail/job_offers_list.html", context)


@require_http_methods(["GET"])
def job_offer_detail(request, offer_id: int):
    """
    Détail d'une offre d'emploi.
    Si ?profile=<id> est présent, on affiche le score de compatibilité.
    """
    offer = get_object_or_404(JobOffer, pk=offer_id)

    profile = None
    match = None
    profile_id = request.GET.get("profile", "").strip()
    if profile_id:
        try:
            profile = UserProfile.objects.get(pk=int(profile_id))
        except (UserProfile.DoesNotExist, ValueError, TypeError):
            profile = None

    if profile is not None:
        match = compute_offer_match(profile, offer)

    return render(
        request,
        "visa_travail/job_offer_detail.html",
        {
            "offer": offer,
            "profile": profile,
            "match": match,
        },
    )


# ============================================================
# 5) TABLEAU DE BORD DES CANDIDATURES (JobApplication)
# ============================================================


@require_http_methods(["GET"])
def job_list(request, profile_id: int):
    """
    Tableau de bord des candidatures pour un profil donné.
    Affiche la liste + quelques stats (total, par statut).
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)

    # Filtres simples (optionnels)
    pays = request.GET.get("pays", "").strip()
    domaine = request.GET.get("domaine", "").strip()
    mot_cle = request.GET.get("q", "").strip()

    qs = JobApplication.objects.filter(user_profile=profile)

    if pays:
        qs = qs.filter(pays__icontains=pays)
    if domaine:
        qs = qs.filter(domaine__icontains=domaine)
    if mot_cle:
        qs = qs.filter(
            Q(titre_poste__icontains=mot_cle)
            | Q(entreprise__icontains=mot_cle)
            | Q(commentaire__icontains=mot_cle)
        )

    applications = qs.order_by("-date_candidature", "-id")

    # Statistiques globales (sans dépendre de constantes du modèle)
    total_applications = applications.count()
    a_faire = applications.filter(statut="A_FAIRE").count()
    en_cours = applications.filter(statut="EN_COURS").count()
    termine = applications.filter(statut="TERMINE").count()

    stats = {
        "total": total_applications,
        "a_faire": a_faire,
        "en_cours": en_cours,
        "termine": termine,
    }

    return render(
        request,
        "visa_travail/job_list.html",
        {
            "profile": profile,
            "applications": applications,
            "stats": stats,
            "pays": pays,
            "domaine": domaine,
            "mot_cle": mot_cle,
        },
    )


@require_http_methods(["GET", "POST"])
def job_create(request, profile_id: int):
    """
    Création manuelle d'une nouvelle candidature JobApplication
    liée à un profil.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)

    if request.method == "POST":
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            job_app = form.save(commit=False)
            job_app.user_profile = profile
            job_app.save()
            return redirect("visa_travail:job_list", profile_id=profile.id)
    else:
        form = JobApplicationForm()

    return render(
        request,
        "visa_travail/job_form.html",
        {
            "profile": profile,
            "form": form,
            "mode": "create",
        },
    )


@require_http_methods(["GET", "POST"])
def job_edit(request, profile_id: int, application_id: int):
    """
    Modification d'une candidature existante.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)
    application = get_object_or_404(
        JobApplication, pk=application_id, user_profile=profile
    )

    if request.method == "POST":
        form = JobApplicationForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            return redirect("visa_travail:job_list", profile_id=profile.id)
    else:
        form = JobApplicationForm(instance=application)

    return render(
        request,
        "visa_travail/job_form.html",
        {
            "profile": profile,
            "form": form,
            "mode": "edit",
            "application": application,
        },
    )


@require_http_methods(["GET", "POST"])
def job_create_from_offer(request, profile_id: int, offer_id: int):
    """
    Crée une candidature pré-remplie à partir d'une JobOffer.
    Permet de transformer rapidement une offre en candidature suivie.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)
    offer = get_object_or_404(JobOffer, pk=offer_id)

    if request.method == "POST":
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            job_app = form.save(commit=False)
            job_app.user_profile = profile
            job_app.save()
            return redirect("visa_travail:job_list", profile_id=profile.id)
    else:
        initial = {
            "titre_poste": offer.titre,
            "entreprise": offer.entreprise,
            "pays": offer.pays,
            "ville": offer.ville,
            "domaine": offer.domaine,
            "lien_offre": offer.lien_candidature,
        }
        form = JobApplicationForm(initial=initial)

    return render(
        request,
        "visa_travail/job_form.html",
        {
            "profile": profile,
            "form": form,
            "mode": "from_offer",
            "offer": offer,
        },
    )


# ============================================================
# 6) COACH CV (ANALYSE SIMPLE + IMPORT FICHIER CV)
# ============================================================


def _extract_text_from_cv_file(uploaded_file) -> Tuple[str, str]:
    """
    Tente d'extraire le texte d'un fichier CV (PDF / DOCX / TXT).
    Retourne (texte, erreur éventuelle).
    Si une librairie n'est pas installée ou le format non supporté,
    on renvoie une chaîne vide et un message d'erreur.
    """
    if not uploaded_file:
        return "", ""

    filename = uploaded_file.name.lower()

    # TXT simple
    if filename.endswith(".txt"):
        try:
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            return content, ""
        except Exception:
            return "", "Impossible de lire le fichier texte envoyé."

    # PDF
    if filename.endswith(".pdf"):
        if PyPDF2 is None:
            return (
                "",
                "Lecture PDF non disponible (librairie PyPDF2 manquante dans l'environnement).",
            )
        try:
            reader = PyPDF2.PdfReader(uploaded_file)
            text_pages: List[str] = []
            for page in reader.pages:
                text_pages.append(page.extract_text() or "")
            return "\n\n".join(text_pages), ""
        except Exception:
            return "", "Impossible d'extraire le texte du PDF. Vérifie que le fichier n'est pas protégé."

    # DOCX
    if filename.endswith(".docx"):
        if docx is None:
            return (
                "",
                "Lecture DOCX non disponible (librairie python-docx manquante).",
            )
        try:
            document = docx.Document(uploaded_file)
            text_paragraphs = [p.text for p in document.paragraphs]
            return "\n".join(text_paragraphs), ""
        except Exception:
            return "", "Impossible d'extraire le texte du fichier Word (DOCX)."

    # Autre format
    return "", "Format de fichier non supporté. Utilise un PDF, DOCX ou TXT."


@require_http_methods(["GET", "POST"])
def coach_cv(request):
    """
    Vue pour analyser le CV via :
    - texte collé directement
    - OU fichier CV importé (PDF / DOCX / TXT) avec extraction automatique

    L'analyse reste volontairement simple (longueur + présence de mots-clés),
    mais tu peux brancher derrière un moteur IA plus avancé.
    """
    analysis_result = None
    upload_error = ""
    uploaded_filename = ""

    if request.method == "POST":
        # On récupère d'abord le fichier s'il existe
        cv_file = request.FILES.get("cv_file")
        post_data = request.POST.copy()

        if cv_file:
            uploaded_filename = cv_file.name
            extracted_text, upload_error = _extract_text_from_cv_file(cv_file)
            if extracted_text:
                # On remplit / complète le champ texte_cv du formulaire
                current_text = post_data.get("texte_cv", "").strip()
                if current_text:
                    combined = f"{current_text}\n\n---\nTexte importé depuis le fichier {uploaded_filename} :\n\n{extracted_text}"
                else:
                    combined = extracted_text
                post_data["texte_cv"] = combined

        # On traite ensuite normalement le formulaire (avec le texte éventuellement pré-rempli)
        form = CVAnalysisForm(post_data)
        if form.is_valid():
            texte_cv = form.cleaned_data["texte_cv"] or ""
            length = len(texte_cv.split())

            # Quelques mots-clés génériques (à adapter selon ton public)
            keywords = [
                "experience",
                "expérience",
                "project",
                "projet",
                "python",
                "java",
                "anglais",
                "lead",
                "gestion",
                "team",
                "équipe",
            ]
            found = [kw for kw in keywords if kw.lower() in texte_cv.lower()]

            messages: List[str] = []

            # Analyse longueur
            if length < 150:
                messages.append(
                    "Ton CV semble très court : pense à détailler davantage tes expériences "
                    "(missions, responsabilités, résultats chiffrés)."
                )
            elif length > 800:
                messages.append(
                    "Ton CV semble très long : essaie de le condenser sur 1 à 2 pages en gardant "
                    "uniquement les expériences les plus pertinentes pour le poste ciblé."
                )
            else:
                messages.append(
                    "La longueur de ton CV semble correcte. Assure-toi que chaque section met en avant "
                    "des résultats concrets (chiffres, impact, réalisations)."
                )

            # Analyse mots-clés
            if not found:
                messages.append(
                    "Je ne retrouve pas beaucoup de mots-clés techniques ou de responsabilités. "
                    "Vérifie que ton CV met clairement en avant les technologies, outils et responsabilités clés "
                    "de ton métier."
                )
            else:
                messages.append(
                    f"Ton CV contient déjà certains mots-clés intéressants : {', '.join(found)}. "
                    "Assure-toi qu'ils apparaissent dans les rubriques 'Expériences' et 'Compétences', "
                    "et qu'ils sont alignés avec les offres de ton pays cible."
                )

            # Petit conseil bonus sur le pays ciblé si le formulaire le contient
            pays_cible = form.cleaned_data.get("pays_cible", "") or ""
            if pays_cible:
                messages.append(
                    f"Pense à adapter ton CV aux standards de {pays_cible} "
                    "(format, photo ou non, structure, vocabulaire)."
                )

            analysis_result = messages
    else:
        form = CVAnalysisForm()

    return render(
        request,
        "visa_travail/coach_cv.html",
        {
            "form": form,
            "analysis_result": analysis_result,
            "upload_error": upload_error,
            "uploaded_filename": uploaded_filename,
        },
    )


# ============================================================
# 7) EXPORT PDF DU PLAN D'ACTION (xhtml2pdf)
# ============================================================


@require_http_methods(["GET"])
def export_plan_pdf(request, profile_id: int):
    """
    Génère un PDF du plan d'action pour un profil donné.
    Utilise xhtml2pdf (pisa) avec un template dédié.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)
    steps = profile.actions.all().order_by("ordre", "id")
    options = recommend_visa_options(profile)
    global_data = compute_global_project_score(profile)

    template = get_template("visa_travail/plan_action_pdf.html")
    html = template.render(
        {
            "profile": profile,
            "steps": steps,
            "options": options,
            "global": global_data,
        }
    )

    response = HttpResponse(content_type="application/pdf")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="plan_visa_travail_{profile.id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        # En cas d'erreur PDF, on renvoie l'HTML brut pour debug
        return HttpResponse("Erreur lors de la génération du PDF.\n\n" + html)

    return response
