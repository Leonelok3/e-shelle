from typing import Dict
from datetime import timedelta
from django.utils import timezone
import re
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.template.loader import get_template
from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.db.models import Q
from collections import defaultdict
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django import forms
from .models import UserProfile, ActionStep, JobApplication, JobOffer
from .forms import (
    UserProfileForm,
    ActionStepStatusForm,
    JobApplicationForm,
    
)
from .visa_data import recommend_visa_options


# ============================================================
#  PAGES PRINCIPALES
# ============================================================
def home(request):
    return render(request, "visa_travail/home.html")


@require_http_methods(["GET", "POST"])
def profil_create(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST)
        if form.is_valid():
            profile = form.save()
            return redirect("visa_travail:resultats", profile_id=profile.pk)
    else:
        form = UserProfileForm()

    return render(request, "visa_travail/profil_form.html", {"form": form})


def resultats(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    options = recommend_visa_options(profile)

    nb_options = len(options)
    pays_suggeres = sorted({opt.get("pays", "") for opt in options if opt.get("pays")})

    context = {
        "profile": profile,
        "options": options,
        "nb_options": nb_options,
        "pays_suggeres": pays_suggeres,
    }
    return render(request, "visa_travail/resultats.html", context)


# ============================================================
#  PLAN D’ACTION + COACH
# ============================================================
def _get_pays_prioritaire(profile: UserProfile, options):
    if options:
        first = options[0]
        pays = first.get("pays")
        if pays:
            return pays

    if profile.pays_cibles:
        first_str = profile.pays_cibles.split(",")[0].strip()
        if first_str:
            return first_str

    return "le pays ciblé"


def _create_default_actions_if_needed(profile: UserProfile, options):
    if profile.actions.exists():
        return

    pays_prioritaire = _get_pays_prioritaire(profile, options)
    programme_names = ", ".join(
        o.get("nom_programme", "") for o in options if o.get("nom_programme")
    )

    steps = []
    ordre = 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Clarifier ton objectif et ton pays prioritaire",
            description=(
                f"Confirmer que {pays_prioritaire} est ta priorité et préciser "
                "le type de poste que tu cibles à l'étranger."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Mettre à jour ton CV au format international",
            description=(
                f"Adapter ton CV au standard du pays ciblé ({pays_prioritaire}) : "
                "structure, mots-clés, longueur, langue."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Optimiser ton profil en ligne (LinkedIn, plateformes emploi)",
            description=(
                "Créer ou optimiser ton profil LinkedIn et t'inscrire sur les sites "
                "d'emploi clés du pays ciblé (Indeed, Jobbank, Pôle Emploi, etc.)."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Rassembler et organiser tes preuves d'expérience",
            description=(
                "Rassembler contrats de travail, attestations d’emploi, fiches de paie "
                "et lettres de recommandation dans un dossier bien structuré."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Vérifier et préparer tes diplômes",
            description=(
                "Scanner tes diplômes, relevés de notes et, si nécessaire, préparer une "
                "évaluation ou reconnaissance (EDE, équivalence, etc.)."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Planifier les tests de langue requis",
            description=(
                "Identifier les tests de langue exigés (IELTS, TOEFL, TEF, TCF, etc.) "
                "et réserver une session pour obtenir le niveau requis."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Créer une routine de candidature hebdomadaire",
            description=(
                "Te fixer un objectif réaliste (par exemple 5 à 10 candidatures ciblées "
                "par semaine) et suivre tes envois dans un tableau simple."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    if programme_names:
        steps.append(
            ActionStep(
                user_profile=profile,
                titre="Étudier les programmes de visa recommandés",
                description=(
                    "Lire en détail les conditions officielles des programmes suivants : "
                    f"{programme_names}. Vérifier ton éligibilité et les étapes exactes."
                ),
                ordre=ordre,
            )
        )
        ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Vérifier la cohérence entre offres d’emploi et type de visa",
            description=(
                "Pour chaque offre intéressante, vérifier si elle est compatible avec "
                "les programmes de visa ciblés et les exigences d’expérience/salaire."
            ),
            ordre=ordre,
        )
    )
    ordre += 1

    steps.append(
        ActionStep(
            user_profile=profile,
            titre="Préparer un dossier numérique complet prêt à envoyer",
            description=(
                "Créer un dossier numérique contenant CV, lettre de motivation, diplômes, "
                "attestations d’expérience, tests de langue et documents d’identité."
            ),
            ordre=ordre,
        )
    )

    ActionStep.objects.bulk_create(steps)


def _build_coach_message(
    profile: UserProfile, progress_percent: int, pays_prioritaire: str
) -> Dict[str, str]:
    domaine = (profile.domaine_metier or "ton domaine").lower()
    horizon = profile.get_horizon_depart_display()

    # Ajustement par pays
    pays_part = ""
    if "canada" in pays_prioritaire.lower():
        pays_part = (
            "Pense à vérifier les exigences de langue (IELTS/TEF) et à regarder les "
            "programmes Entrée Express et PNP de la province qui t'intéresse. "
        )
    elif "allemagne" in pays_prioritaire.lower():
        pays_part = (
            "La reconnaissance de diplôme et un minimum d’allemand (B1/B2) seront "
            "des leviers clés. "
        )
    elif "france" in pays_prioritaire.lower():
        pays_part = (
            "Travaille bien ton CV à la française et regarde si tu entres dans un "
            "dispositif comme Passeport Talent. "
        )
    elif "royaume" in pays_prioritaire.lower() or "uk" in pays_prioritaire.lower():
        pays_part = (
            "Assure-toi de cibler des employeurs qui ont une licence de sponsor et "
            "de viser le bon seuil de salaire. "
        )

    # Ajustement par domaine
    if "ingén" in domaine or "engineer" in domaine:
        domaine_part = (
            "Les profils d’ingénierie sont très recherchés : mets bien en avant tes "
            "projets concrets, tes logiciels et tes certifications. "
        )
    elif "informat" in domaine or "dev" in domaine:
        domaine_part = (
            "En informatique, un GitHub propre et un bon profil LinkedIn peuvent faire "
            "la différence. Pense aussi aux offres en full remote. "
        )
    elif "santé" in domaine or "infirm" in domaine or "médec" in domaine:
        domaine_part = (
            "Les métiers de la santé demandent souvent reconnaissance d’équivalence "
            "et parfois un niveau de langue plus élevé : anticipe ces démarches. "
        )
    elif "enseign" in domaine or "prof" in domaine:
        domaine_part = (
            "Pour l’enseignement, regarde les programmes d’écoles internationales, "
            "les académies privées et les dispositifs publics de recrutement. "
        )
    else:
        domaine_part = (
            "Met ton expérience la plus pertinente en avant et cible des offres qui "
            "demandent réellement ton type de profil. "
        )

    if progress_percent == 0:
        titre = "On démarre ensemble 🚀"
        corps = (
            f"Tu viens d’ouvrir ton plan d’action pour {pays_prioritaire}. "
            "Commence par les 2 premières étapes : clarifier ton projet et mettre ton CV "
            "au standard du pays. Une fois ces deux points faits, tu auras déjà posé "
            "des bases très solides pour décrocher un emploi. "
        )
    elif progress_percent < 30:
        titre = "Très bon début 💡"
        corps = (
            f"Tu as déjà enclenché le mouvement vers {pays_prioritaire}. "
            "Concentre-toi maintenant sur la partie preuves d’expérience et diplômes. "
            "Plus ton dossier est clair et structuré, plus les recruteurs te prendront "
            "au sérieux. "
        )
    elif progress_percent < 60:
        titre = "Tu es en route ✅"
        corps = (
            "Tu as déjà couvert une bonne partie des bases. C’est le bon moment pour : "
            "1) finaliser tes documents, 2) mettre à jour LinkedIn, 3) lancer une routine "
            "de candidatures hebdomadaire. "
            f"Si tu maintiens le rythme, ton objectif sur {horizon} reste jouable. "
        )
    elif progress_percent < 90:
        titre = "Dernière ligne droite 🔥"
        corps = (
            "Ton dossier commence à ressembler à celui d’un candidat prêt à être recruté. "
            "Continue à postuler régulièrement, vérifie bien l’adéquation entre chaque "
            "offre et les programmes de visa, et suis tes réponses. "
        )
    else:
        titre = "Dossier presque prêt 🎯"
        corps = (
            "Bravo, tu as presque tout bouclé. À partir de maintenant, ton focus doit être : "
            "candidatures ciblées, suivi sérieux, préparation aux entretiens et "
            "vérification des exigences officielles sur les sites gouvernementaux. "
        )

    message = corps + pays_part + domaine_part
    return {"titre": titre, "message": message}


@require_http_methods(["GET", "POST"])
def plan_action(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    options = recommend_visa_options(profile)

    _create_default_actions_if_needed(profile, options)

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
    progress_percent = int((done_steps / total_steps) * 100) if total_steps else 0

    if progress_percent < 30:
        progress_label = "Démarrage"
    elif progress_percent < 80:
        progress_label = "En route"
    else:
        progress_label = "Dossier presque prêt"

    pays_prioritaire = _get_pays_prioritaire(profile, options)
    coach = _build_coach_message(profile, progress_percent, pays_prioritaire)

    return render(
        request,
        "visa_travail/plan_action.html",
        {
            "profile": profile,
            "steps": steps,
            "progress_percent": progress_percent,
            "progress_label": progress_label,
            "total_steps": total_steps,
            "done_steps": done_steps,
            "coach_title": coach["titre"],
            "coach_message": coach["message"],
            "pays_prioritaire": pays_prioritaire,
        },
    )


@require_http_methods(["GET", "POST"])
def coach_cv(request):
    """
    Coach CV – l'utilisateur colle son CV + poste + pays.
    Retourne une analyse et des recommandations.
    """
    analysis = None
    profile = None

    if request.method == "POST":
        form = CVAnalysisForm(request.POST)
        if form.is_valid():
            user_profile = form.cleaned_data.get("user_profile")
            intitule_poste = form.cleaned_data["intitule_poste"]
            pays_cible = form.cleaned_data["pays_cible"]
            cv_texte = form.cleaned_data["cv_texte"]

            if user_profile:
                profile = user_profile

            analysis = analyze_cv_text(cv_texte, intitule_poste, pays_cible)
    else:
        form = CVAnalysisForm()

    return render(
        request,
        "visa_travail/coach_cv.html",
        {
            "form": form,
            "analysis": analysis,
            "profile": profile,
        },
    )


# ============================================================
#  MODULE 2 : CANDIDATURES (JOB TRACKER)
# ============================================================
def job_list(request, profile_id):
    """
    Tableau de bord des candidatures pour un profil donné.
    Dashboard avec stats + filtres + tableau.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)
    applications = profile.job_applications.all().order_by("-date_candidature", "-date_creation")

    # Filtres simples
    statut = request.GET.get("statut", "").strip()
    pays = request.GET.get("pays", "").strip()

    if statut:
        applications = applications.filter(statut=statut)
    if pays:
        applications = applications.filter(pays__icontains=pays)

    # Statistiques globales
    total = profile.job_applications.count()
    count_a_postuler = profile.job_applications.filter(statut="A_POSTULER").count()
    count_envoyee = profile.job_applications.filter(statut="ENVOYEE").count()
    count_entretien = profile.job_applications.filter(statut="ENTRETIEN").count()
    count_acceptee = profile.job_applications.filter(statut="ACCEPTEE").count()
    count_refusee = profile.job_applications.filter(statut="REFUSEE").count()

    active = count_envoyee + count_entretien
    success_rate = round((count_acceptee / total) * 100) if total > 0 else 0

    # Candidatures des 30 derniers jours
    today = timezone.now().date()
    last_30_days_count = profile.job_applications.filter(
        date_candidature__isnull=False,
        date_candidature__gte=today - timedelta(days=30),
    ).count()

    context = {
        "profile": profile,
        "applications": applications,
        "statut": statut,
        "pays": pays,
        "total": total,
        "count_a_postuler": count_a_postuler,
        "count_envoyee": count_envoyee,
        "count_entretien": count_entretien,
        "count_acceptee": count_acceptee,
        "count_refusee": count_refusee,
        "active": active,
        "success_rate": success_rate,
        "last_30_days_count": last_30_days_count,
    }
    return render(request, "visa_travail/job_list.html", context)


@require_http_methods(["GET", "POST"])
def job_create(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)

    if request.method == "POST":
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.user_profile = profile
            job.save()
            return redirect("visa_travail:job_list", profile_id=profile.pk)
    else:
        form = JobApplicationForm()

    return render(
        request,
        "visa_travail/job_form.html",
        {"profile": profile, "form": form, "is_edit": False},
    )


@require_http_methods(["GET", "POST"])
def job_update(request, job_id):
    job = get_object_or_404(JobApplication, pk=job_id)
    profile = job.user_profile

    if request.method == "POST":
        form = JobApplicationForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            return redirect("visa_travail:job_list", profile_id=profile.pk)
    else:
        form = JobApplicationForm(instance=job)

    return render(
        request,
        "visa_travail/job_form.html",
        {"profile": profile, "form": form, "is_edit": True, "job": job},
    )


@require_http_methods(["POST"])
def job_update_status(request, job_id):
    job = get_object_or_404(JobApplication, pk=job_id)
    form = JobApplicationStatusForm(request.POST, instance=job)
    if form.is_valid():
        form.save()
    return redirect("visa_travail:job_list", profile_id=job.user_profile.pk)


# ============================================================
#  MODULE 3 : EXPORT PDF DU PLAN
# ============================================================
def export_plan_pdf(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    steps = profile.actions.all()

    response = HttpResponse(content_type="application/pdf")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="plan_visa_travail_{profile_id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Plan d'action Visa Travail")
    y -= 25

    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Pays ciblés : {profile.pays_cibles}")
    y -= 15
    p.drawString(50, y, f"Domaine : {profile.domaine_metier}")
    y -= 15
    p.drawString(50, y, f"Horizon de départ : {profile.get_horizon_depart_display()}")
    y -= 25

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Étapes :")
    y -= 20

    p.setFont("Helvetica", 10)
    for idx, step in enumerate(steps, start=1):
        if y < 70:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 10)

        statut_label = step.get_statut_display()
        p.drawString(50, y, f"{idx}. {step.titre} [{statut_label}]")
        y -= 14

        if step.description:
            lines = []
            text = step.description
            max_len = 90
            while len(text) > max_len:
                split_at = text.rfind(" ", 0, max_len)
                if split_at == -1:
                    split_at = max_len
                lines.append(text[:split_at])
                text = text[split_at:].lstrip()
            if text:
                lines.append(text)

            for line in lines:
                if y < 70:
                    p.showPage()
                    y = height - 50
                    p.setFont("Helvetica", 10)
                p.drawString(60, y, line)
                y -= 12

        y -= 6

    p.showPage()
    p.save()
    return response

# ============================================================
#  JOB BOARD – OFFRES D’EMPLOI PUBLIQUES
# ============================================================
def job_offers_list(request):
    """
    Liste des offres d'emploi disponibles, avec filtres simples par pays et domaine.
    Les offres sont saisies par l'admin dans le back-office.
    """
    pays = request.GET.get("pays", "").strip()
    domaine = request.GET.get("domaine", "").strip()

    offers = JobOffer.objects.filter(est_active=True)

    if pays:
        offers = offers.filter(pays__icontains=pays)

    if domaine:
        offers = offers.filter(
            Q(domaine__icontains=domaine) | Q(titre__icontains=domaine)
        )

    offers = offers.order_by("priorite", "-date_publication")

    context = {
        "offers": offers,
        "pays": pays,
        "domaine": domaine,
    }
    return render(request, "visa_travail/job_offers_list.html", context)


def job_offer_detail(request, offer_id):
    """
    Détail d'une offre d'emploi.
    """
    offer = get_object_or_404(JobOffer, pk=offer_id, est_active=True)
    return render(
        request,
        "visa_travail/job_offer_detail.html",
        {"offer": offer},
    )




# ============================================================
#  JOB TRACKER – CANDIDATURES PAR PROFIL
# ============================================================
def coach_analysis(profile, stats):
    """
    Analyse IA simple (offline) basée sur les stats du dashboard.
    Retourne un dictionnaire {title, advice, priority, week_plan}
    """

    total = stats["total"]
    env = stats["count_envoyee"]
    entretien = stats["count_entretien"]
    accepte = stats["count_acceptee"]
    refuse = stats["count_refusee"]
    to_apply = stats["count_a_postuler"]
    success = stats["success_rate"]
    active = stats["active"]
    recent = stats["last_30_days_count"]

    # -------------------------------
    # 1. Détermination du niveau de progression
    # -------------------------------
    if success >= 20:
        level = "excellent"
    elif success >= 10:
        level = "bon"
    elif success >= 5:
        level = "moyen"
    else:
        level = "faible"

    # -------------------------------
    # 2. Diagnostic IA intelligent
    # -------------------------------
    if total == 0:
        advice = (
            "Tu n’as pas encore commencé à postuler. Avant toute chose, sélectionne 5 à 10 "
            "offres pertinentes et envoie rapidement des candidatures adaptées à ton profil."
        )
        priority = "Urgence maximale"
    elif success == 0 and entretien == 0 and env > 0:
        advice = (
            "Tu as envoyé plusieurs candidatures mais aucune réponse ni entretien. "
            "Il faut revoir ton CV, tes lettres et ton ciblage : probablement ton dossier "
            "ne passe pas les filtres automatiques."
        )
        priority = "Urgence élevée"
    elif entretien > 0 and success == 0:
        advice = (
            "Tu obtiens des entretiens mais pas d’acceptation. Le problème se situe "
            "probablement dans ta préparation aux entretiens ou dans la correspondance "
            "entre ton profil et les exigences des recruteurs."
        )
        priority = "Priorité forte"
    elif accepte > 0 and accepte < env:
        advice = (
            "Tu progresses bien. Tu as déjà des réponses positives. Continue à postuler "
            "en te focalisant sur les offres où ton profil correspond à 80% ou plus."
        )
        priority = "Normal"
    else:
        advice = (
            "Bonne dynamique ! Continue à optimiser ton ciblage et ton argumentaire "
            "pour maximiser les chances de réponses positives."
        )
        priority = "Normal"

    # -------------------------------
    # 3. Plan d'action sur 7 jours
    # -------------------------------
    week_plan = [
        "📌 Jour 1 : Optimiser ton CV pour les ATS + ajouter mots-clés du pays ciblé.",
        "📌 Jour 2 : Identifier 15 nouvelles offres dans 3 pays prioritaires.",
        "📌 Jour 3 : Adapter ta lettre de motivation pour 5 entreprises différentes.",
        "📌 Jour 4 : Simuler un entretien (questions classiques + technique).",
        "📌 Jour 5 : Mettre à jour ton profil LinkedIn + activer 'Open to work'.",
        "📌 Jour 6 : Envoyer au moins 8 candidatures ultra ciblées.",
        "📌 Jour 7 : Faire un bilan des réponses reçues + ajuster le ciblage.",
    ]

    return {
        "title": f"Niveau actuel : {level.capitalize()}",
        "advice": advice,
        "priority": priority,
        "week_plan": week_plan,
    }



def analyze_cv_text(cv_text: str, intitule_poste: str, pays_cible: str) -> dict:
    """
    Analyse simple du CV : structure, sections, mots-clés.
    Retourne un dict avec scores et recommandations.
    """
    text = cv_text.lower()

    sections = {
        "experience": any(word in text for word in ["expérience", "experience professionnelle", "professional experience"]),
        "formation": any(word in text for word in ["formation", "éducation", "diplôme", "education"]),
        "competences": any(word in text for word in ["compétences", "skills"]),
        "langues": any(word in text for word in ["langues", "languages", "bilingue", "anglais", "français"]),
        "coordonnees": any(word in text for word in ["téléphone", "email", "mail", "contact"]),
    }

    structure_score = sum(1 for v in sections.values() if v) / len(sections) * 100

    missing_sections = [name for name, present in sections.items() if not present]

    poste_norm = re.sub(r"[^a-z0-9 ]", "", intitule_poste.lower())
    mots_poste = [m for m in poste_norm.split() if len(m) > 3]

    keyword_hits = 0
    for m in mots_poste:
        if m in text:
            keyword_hits += 1

    keyword_score = int((keyword_hits / max(len(mots_poste), 1)) * 100) if mots_poste else 0

    pays_keywords = {
        "canada": ["canada", "québec", "quebec", "ottawa", "toronto", "montreal", "montréal"],
        "france": ["france", "paris", "lyon", "marseille"],
        "allemagne": ["germany", "deutschland", "berlin", "munich", "munchen", "münchen"],
        "belgique": ["belgique", "bruxelles", "brussels"],
        "royaume-uni": ["uk", "united kingdom", "london"],
    }
    pays_norm = pays_cible.lower().strip()
    pays_score = 0
    for key, kw_list in pays_keywords.items():
        if key in pays_norm:
            if any(k in text for k in kw_list):
                pays_score = 80
            else:
                pays_score = 40
            break

    global_score = int((structure_score * 0.4) + (keyword_score * 0.4) + (pays_score * 0.2))

    if global_score >= 80:
        level = "CV très solide pour un visa travail."
    elif global_score >= 60:
        level = "CV correct mais améliorable pour un visa travail."
    elif global_score >= 40:
        level = "CV à retravailler pour être compétitif à l’international."
    else:
        level = "CV trop faible pour des candidatures sérieuses à l’étranger."

    suggestions = []

    if missing_sections:
        readable = ", ".join(missing_sections)
        suggestions.append(
            f"Ajoute ou renforce les sections suivantes : {readable}."
        )

    if keyword_score < 70:
        suggestions.append(
            "Ajoute davantage de mots-clés en lien direct avec le poste ciblé (technologies, outils, responsabilités)."
        )

    if structure_score < 70:
        suggestions.append(
            "Revoir la structure générale : titres clairs, sections séparées, listes à puces pour les missions."
        )

    if pays_score < 60:
        suggestions.append(
            f"Ajoute des éléments qui montrent que tu cibles réellement {pays_cible} "
            "(format de CV adapté, vocabulaire du pays, références pertinentes)."
        )

    if not suggestions:
        suggestions.append(
            "Ton CV semble déjà bien structuré. Tu peux encore l’améliorer en le traduisant dans la langue du pays ciblé "
            "et en alignant les mots-clés avec les offres auxquelles tu postules."
        )

    return {
        "structure_score": int(structure_score),
        "keyword_score": int(keyword_score),
        "country_score": int(pays_score),
        "global_score": global_score,
        "level": level,
        "missing_sections": missing_sections,
        "suggestions": suggestions,
    }

############### coach niveau 2 #################

import re
from collections import defaultdict

def normalize(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9 ]", "", text.lower()).strip()

def keyword_match_score(text1: str, text2: str) -> int:
    """
    Compare deux textes et renvoie un score sur 100.
    """
    t1 = normalize(text1).split()
    t2 = normalize(text2).split()
    if not t1 or not t2:
        return 0

    intersection = set(t1).intersection(set(t2))
    if not intersection:
        return 0

    score = int((len(intersection) / len(t1)) * 100)
    return min(score, 100)


def coach_country_matching(profile, offers):
    """
    Analyse par pays + matching automatique avec le métier du profil.
    """

    domaine = profile.domaine_metier
    pays_cibles = [p.strip() for p in profile.pays_cibles.split(",")]

    # Stats par pays
    country_stats = defaultdict(lambda: {"total": 0, "matches": 0, "best_scores": []})

    top_offers = []

    for offer in offers:
        country_stats[offer.pays]["total"] += 1

        # matching métier ↔ offre
        score = keyword_match_score(domaine, offer.titre + " " + (offer.domaine or ""))

        if score > 20:  # seuil minimal
            country_stats[offer.pays]["matches"] += 1
            country_stats[offer.pays]["best_scores"].append(score)

            top_offers.append((score, offer))

    # classement offres
    top_offers = sorted(top_offers, key=lambda x: x[0], reverse=True)[:5]

    # classement pays
    ranked_countries = []
    for country, data in country_stats.items():
        if data["total"] == 0:
            continue

        match_rate = int((data["matches"] / data["total"]) * 100)
        avg_score = int(sum(data["best_scores"]) / len(data["best_scores"])) if data["best_scores"] else 0

        ranked_countries.append({
            "country": country,
            "total_offers": data["total"],
            "matches": data["matches"],
            "match_rate": match_rate,
            "avg_score": avg_score,
            "is_target": country in pays_cibles,
        })

    ranked_countries = sorted(ranked_countries, key=lambda x: (x["is_target"], x["avg_score"], x["match_rate"]), reverse=True)[:3]

    return {
        "ranked_countries": ranked_countries,
        "top_offers": [o[1] for o in top_offers],
    }




def job_list(request, profile_id):
    """
    Tableau de bord des candidatures pour un profil donné.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)
    applications = profile.job_applications.all().order_by("-date_creation")

    statut = request.GET.get("statut", "").strip()
    pays = request.GET.get("pays", "").strip()

    if statut:
        applications = applications.filter(statut=statut)
    if pays:
        applications = applications.filter(pays__icontains=pays)
        country_ai = coach_country_matching(profile, offers)


    context = {
        "profile": profile,
        "applications": applications,
        "statut": statut,
        "pays": pays,
        "coach": coach_analysis(profile, {
        "total": total,
        "count_a_postuler": count_a_postuler,
        "count_envoyee": count_envoyee,
        "count_entretien": count_entretien,
        "count_acceptee": count_acceptee,
        "count_refusee": count_refusee,
        "success_rate": success_rate,
        "active": active,
        "last_30_days_count": last_30_days_count,
        "country_ai": country_ai,
    }),

    }
    return render(request, "visa_travail/job_list.html", context)


@require_http_methods(["GET", "POST"])
def job_create(request, profile_id):
    """
    Créer une nouvelle candidature pour un profil donné.
    """
    profile = get_object_or_404(UserProfile, pk=profile_id)

    if request.method == "POST":
        form = JobApplicationForm(request.POST)
        # On force le profil dans la candidature
        if form.is_valid():
            application = form.save(commit=False)
            application.user_profile = profile
            application.save()
            return redirect("visa_travail:job_list", profile_id=profile.id)
    else:
        # Pré-remplir pays avec le premier pays cible s'il existe
        initial = {}
        if profile.pays_cibles:
            initial["pays"] = profile.pays_cibles.split(",")[0].strip()
        form = JobApplicationForm(initial=initial)
        # On masque le champ user_profile dans ce cas
        form.fields["user_profile"].widget = forms.HiddenInput()
        form.fields["user_profile"].initial = profile.id

    return render(
        request,
        "visa_travail/job_form.html",
        {
            "form": form,
            "profile": profile,
            "is_edit": False,
        },
    )


@require_http_methods(["GET", "POST"])
def job_update(request, job_id):
    """
    Modifier une candidature existante.
    """
    application = get_object_or_404(JobApplication, pk=job_id)
    profile = application.user_profile

    if request.method == "POST":
        form = JobApplicationForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            return redirect("visa_travail:job_list", profile_id=profile.id)
    else:
        form = JobApplicationForm(instance=application)
        # On masque le champ user_profile pour éviter de le changer ici
        form.fields["user_profile"].widget = forms.HiddenInput()

    return render(
        request,
        "visa_travail/job_form.html",
        {
            "form": form,
            "profile": profile,
            "is_edit": True,
        },
    )


@require_http_methods(["POST"])
def job_update_status(request, job_id):
    """
    Mise à jour rapide du statut d'une candidature (depuis la liste).
    """
    application = get_object_or_404(JobApplication, pk=job_id)
    new_status = request.POST.get("statut", "").strip()
    valid_status = dict(JobApplication.STATUT_CHOICES).keys()

    if new_status in valid_status:
        application.statut = new_status
        application.save()

    return redirect("visa_travail:job_list", profile_id=application.user_profile.id)


@require_http_methods(["GET", "POST"])
def job_create_from_offer(request, offer_id):
    """
    Créer une candidature à partir d'une offre d'emploi du job board.
    L'utilisateur choisit à quel profil l'associer.
    """
    offer = get_object_or_404(JobOffer, pk=offer_id, est_active=True)

    if request.method == "POST":
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save()
            return redirect(
                "visa_travail:job_list",
                profile_id=application.user_profile.id,
            )
    else:
        initial = {
            "titre_poste": offer.titre,
            "entreprise": offer.entreprise,
            "pays": offer.pays,
            "ville": offer.ville,
            "lien_offre": offer.lien_candidature,
            "source": "Job board Visa Travail",
        }
        form = JobApplicationForm(initial=initial)

    return render(
        request,
        "visa_travail/job_form.html",
        {
            "form": form,
            "offer": offer,
            "profile": None,
            "is_edit": False,
            "from_offer": True,
        },
    )

#############===================================================================
#####=================PLAN PDF ++++++++++++++++++++++++++++++++    
def export_plan_pdf(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    steps = profile.actions.all()

    total_steps = steps.count()
    done_steps = steps.filter(statut=ActionStep.STATUT_TERMINE).count()
    progress_percent = int((done_steps / total_steps) * 100) if total_steps > 0 else 0

    if progress_percent == 0:
        progress_label = "Début du parcours"
    elif progress_percent < 40:
        progress_label = "Tu es en phase de lancement"
    elif progress_percent < 80:
        progress_label = "Bonne progression"
    else:
        progress_label = "Tu es tout près du but 🎯"

    context = {
        "profile": profile,
        "steps": steps,
        "total_steps": total_steps,
        "done_steps": done_steps,
        "progress_percent": progress_percent,
        "progress_label": progress_label,
    }

    template_path = "visa_travail/plan_pdf.html"
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="plan_visa_travail_{profile.id}.pdf"'

    pisa_status = pisa.CreatePDF(
        html, dest=response
    )

    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)
    return response

# ============================================================
#  RESSOURCES
# ============================================================
def ressources(request):
    return render(request, "visa_travail/ressources.html")
