from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings
import json
import openai

from .forms import PREligibilityForm
from .models import (
    PRProfile,
    PRPlanStep,
    ImmigrationProgram,
    ProgramResource,
)
from .programs_config import evaluate_profile


# -------------------------------------------------------------------
#  PAGE D’ACCUEIL DU MODULE RP
# -------------------------------------------------------------------
@login_required
def home_view(request):
    """
    Page d'accueil du module Résidence Permanente.
    Présente le module, avec liens vers :
    - simulateur d'éligibilité
    - plan d’action
    - guides programmes, etc.
    """
    return render(request, "permanent_residence/home.html")


# -------------------------------------------------------------------
#  LOGIQUE D’ÉVALUATION SIMPLIFIÉE (non officielle)
# -------------------------------------------------------------------
def evaluate_eligibility(profile: PRProfile) -> dict:
    """
    Évaluation très simplifiée / indicative.
    Ce n'est PAS un calcul officiel de points.
    """
    reasons = []
    suggestions = []

    age = profile.age or 0
    exp_years = profile.years_experience or 0
    edu = (profile.education_level or "").strip()
    fr = (profile.french_level or "").strip()
    en = (profile.english_level or "").strip()

    likely = True

    # Âge
    if 18 <= age <= 44:
        reasons.append("Âge dans une plage généralement favorable pour l'immigration économique.")
    elif age == 0:
        likely = False
        suggestions.append("Indique ton âge pour mieux évaluer ton éligibilité.")
    else:
        reasons.append("Âge potentiellement plus difficile pour certains programmes basés sur les points.")
        suggestions.append(
            "Vise des programmes moins sensibles à l'âge (certains PNP, sponsorisation employeur, etc.)."
        )

    # Études
    if edu:
        reasons.append(f"Niveau d'études déclaré : {edu}.")
    else:
        likely = False
        suggestions.append(
            "Indique ton niveau d'études (Bac, Licence, Master...) pour cibler les bons programmes."
        )

    # Expérience
    if exp_years >= 1:
        reasons.append(f"Expérience professionnelle : {exp_years} an(s) ou plus.")
    else:
        suggestions.append(
            "Les programmes de RP exigent souvent au moins 1 an d'expérience qualifiée à temps plein."
        )

    # Langues
    if fr or en:
        reasons.append("Tu as déjà indiqué un niveau en français et/ou en anglais.")
        suggestions.append(
            "Vérifie les tests officiels exigés (TEF/TCF, IELTS, PTE...) et les scores à viser."
        )
    else:
        likely = False
        suggestions.append(
            "Les programmes RP exigent presque toujours un test de langue officiel. "
            "Prévois de passer un test (TEF/TCF pour le français, IELTS/PTE pour l'anglais)."
        )

    # Liens / job offer
    if profile.has_family_in_country:
        reasons.append("Tu as de la famille dans le pays visé, ce qui peut aider pour certains programmes.")
    if profile.has_job_offer:
        reasons.append(
            "Tu as une offre d'emploi, ce qui peut renforcer ton dossier pour plusieurs voies RP."
        )

    # Statut global
    if not likely:
        status = "profil_incomplet_ou_faible"
        summary = (
            "Sur la base des informations fournies, ton profil semble encore incomplet ou peu compétitif. "
            "Ce n'est pas un refus : il faut surtout renforcer certains points clés."
        )
    elif exp_years >= 1 and (fr or en) and edu:
        status = "profil_potentiellement_interessant"
        summary = (
            "Ton profil semble potentiellement intéressant pour au moins une voie de résidence permanente, "
            "mais il faudra vérifier les détails sur les sites officiels et affiner ton projet."
        )
    else:
        status = "profil_a_renforcer"
        summary = (
            "Ton profil présente des éléments positifs, mais certains aspects restent à renforcer "
            "pour être compétitif sur les principaux programmes."
        )

    return {
        "status": status,
        "summary": summary,
        "reasons": reasons,
        "suggestions": suggestions,
    }


# -------------------------------------------------------------------
#  FORMULAIRE ÉLIGIBILITÉ RP + REDIRECT VERS PAGE RÉSULTAT
# -------------------------------------------------------------------
@login_required
def eligibility_view(request):
    """
    GET  -> affiche le formulaire RP
    POST -> enregistre le profil + crée les étapes du plan + redirige
            vers la page de résultat ultra premium.
    """
    if request.method == "POST":
        form = PREligibilityForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

            # Générer un plan d’action de base pour ce profil
            _generate_default_steps(profile)

            # On redirige vers la page de résultat
            return redirect("permanent_residence:result", pk=profile.pk)
    else:
        form = PREligibilityForm()

    # Affichage du formulaire
    return render(
        request,
        "permanent_residence/eligibility_form.html",
        {"form": form},
    )


# -------------------------------------------------------------------
#  PAGE RÉSULTAT (TON TEMPLATE ULTRA PREMIUM)
# -------------------------------------------------------------------
@login_required
def eligibility_result_view(request, pk):
    """
    Affiche la page résultat RP pour un profil donné.
    Utilise ton template permanent_residence/eligibility_result.html
    avec :
      - profile
      - evaluation (dict)
      - program_results (liste de programmes suggérés)
      - progress_percent (progression du plan d’action)
    """
    profile = get_object_or_404(PRProfile, pk=pk, user=request.user)

    # Évaluation simplifiée
    evaluation = evaluate_eligibility(profile)

    # Résultats des programmes (Canada / Australie)
    program_results = evaluate_profile(profile)

    # Progression basée sur les étapes du plan
    all_steps = list(profile.steps.all())
    total_steps = len(all_steps)
    done_steps = len([s for s in all_steps if s.status == "done"])
    progress_percent = int(done_steps * 100 / total_steps) if total_steps > 0 else 0

    return render(
        request,
        "permanent_residence/eligibility_result.html",
        {
            "profile": profile,
            "evaluation": evaluation,
            "program_results": program_results,
            "progress_percent": progress_percent,
        },
    )


# -------------------------------------------------------------------
#  GÉNÉRATION DES ÉTAPES DE PLAN PAR DÉFAUT
# -------------------------------------------------------------------
def _generate_default_steps(profile: PRProfile) -> None:
    """
    Crée les étapes standard du plan RP pour ce profil,
    uniquement si aucune étape n'existe encore.
    """
    if profile.steps.exists():
        return

    steps_data = []

    # 1. Étape générale : clarifier le projet
    steps_data.append({
        "title": "Clarifier ton projet RP (pays, voie principale)",
        "description": (
            "Choisir ton pays (Canada/Australie) et les voies possibles : "
            "Entrée Express, PNP, Skilled visa, sponsor employeur, etc."
        ),
    })

    # 2. Langues
    steps_data.append({
        "title": "Évaluer et améliorer ton niveau de langue",
        "description": (
            "Identifier les tests à passer (TEF/TCF, IELTS, PTE…) et les scores à viser "
            "pour ton programme cible (CLB 7, CLB 9, score 65+ pour l’Australie, etc.)."
        ),
    })

    # 3. Diplômes / EDE
    steps_data.append({
        "title": "Faire reconnaître tes diplômes",
        "description": (
            "Lancer l’évaluation des études (EDE pour le Canada, skills assessment pour "
            "l’Australie) si nécessaire."
        ),
    })

    # 4–5. Spécifique CANADA
    if profile.country == "CA":
        steps_data.extend([
            {
                "title": "Construire ta stratégie Entrée Express / PNP / Mobilité",
                "description": (
                    "Choisir entre Entrée Express, Programmes des candidats des provinces (PNP), "
                    "Mobilité francophone ou autres voies, selon ton profil."
                ),
            },
            {
                "title": "Préparer les documents pour IRCC",
                "description": (
                    "Passeport, attestations d’emploi, EDE, résultats de tests de langue, "
                    "preuves de fonds, casiers judiciaires, photos, formulaires IRCC, etc."
                ),
            },
        ])

    # 4–5. Spécifique AUSTRALIE
    if profile.country == "AU":
        steps_data.extend([
            {
                "title": "Choisir le bon visa australien (189, 190, 491, sponsor…)",
                "description": (
                    "Vérifier la présence de ton métier sur les listes éligibles, "
                    "et décider si tu vises un visa à points (189/190/491) ou un sponsor employeur."
                ),
            },
            {
                "title": "Préparer les documents pour Home Affairs",
                "description": (
                    "Passeport, skills assessment, résultats d’anglais, références d’emploi, "
                    "extraits de casier, documents familiaux, etc."
                ),
            },
        ])

    # Création effective des étapes (pas de champ category ici, on reste simple)
    for idx, data in enumerate(steps_data, start=1):
        PRPlanStep.objects.create(
            profile=profile,
            order=idx,
            title=data["title"],
            description=data["description"],
            status="todo",
        )


# -------------------------------------------------------------------
#  PAGE PLAN D’ACTION RP
# -------------------------------------------------------------------
@login_required
def plan_view(request, pk: int):
    """
    Affiche le plan d’action RP + permet de changer le statut des étapes.
    URL : /pr/plan/<pk>/
    pk = id du PRProfile
    """
    profile = get_object_or_404(PRProfile, pk=pk, user=request.user)

    # Génère les étapes si nécessaire
    _generate_default_steps(profile)

    # Gestion du changement de statut
    if request.method == "POST":
        step_id = request.POST.get("step_id")
        new_status = request.POST.get("status")
        category = request.GET.get("category", "all")

        if step_id and new_status in dict(PRPlanStep.STATUS_CHOICES):
            step = get_object_or_404(PRPlanStep, pk=step_id, profile=profile)
            step.status = new_status
            step.save()

        return redirect(f"{request.path}?category={category}")

    # Filtre par catégorie (si tu utilises un champ category dans PRPlanStep)
    category = request.GET.get("category", "all")
    all_steps = list(profile.steps.all())

    if category == "all":
        steps = all_steps
    else:
        steps = [s for s in all_steps if getattr(s, "category", None) == category]

    # Progression globale
    total_steps = len(all_steps)
    done_steps = len([s for s in all_steps if s.status == "done"])
    progress_pct = int(done_steps * 100 / total_steps) if total_steps > 0 else 0

    context = {
        "profile": profile,
        "steps": steps,
        "category": category,
        "progress_pct": progress_pct,
    }
    return render(request, "permanent_residence/plan.html", context)


# -------------------------------------------------------------------
#  API COACH IA RP (mini-chat JSON)
# -------------------------------------------------------------------
@csrf_exempt
@require_POST
def rp_coach_api(request, profile_id):
    """
    Endpoint JSON pour le Coach IA RP.
    Reçoit { "message": "..."} et renvoie { "answer": "..." }.
    """
    profile = get_object_or_404(PRProfile, pk=profile_id)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Requête invalide."}, status=400)

    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message vide."}, status=400)

    # Si la clé n'est pas configurée, on répond proprement
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        fallback = (
            "Le coach IA n'est pas encore configuré côté serveur (clé OpenAI manquante).\n\n"
            "Demande à l'administrateur d'ajouter OPENAI_API_KEY dans les paramètres "
            "pour activer les réponses automatiques."
        )
        return JsonResponse({"answer": fallback})

    openai.api_key = api_key

    # Contexte profil pour que l'IA réponde de manière ultra ciblée
    country_label = (
        "Canada"
        if str(profile.country).lower() in ["ca", "canada"]
        else "Australie"
        if str(profile.country).upper() == "AU"
        else str(profile.country)
    )

    profil_context = f"""
    Contexte profil RP de l'utilisateur :
    - Pays ciblé : {country_label}
    - Âge : {getattr(profile, 'age', '') or '-'}
    - Niveau d'études : {getattr(profile, 'education_level', '') or '-'}
    - Années d'expérience : {getattr(profile, 'years_experience', '') or '-'}
    - Niveau global de français : {getattr(profile, 'french_level', '') or '-'}
    - Niveau global d'anglais : {getattr(profile, 'english_level', '') or '-'}
    - Profession principale : {getattr(profile, 'profession_title', '') or '-'}
    - Famille sur place : {"Oui" if getattr(profile, "has_family_in_country", False) else "Non"}
    - Offre d'emploi : {"Oui" if getattr(profile, "has_job_offer", False) else "Non"}
    """

    system_prompt = (
        "Tu es un coach d'immigration ultra pédagogique et réaliste, spécialisé en Résidence "
        "Permanente Canada (Entrée Express, PNP) et Australie (Skilled visas, State nomination).\n\n"
        "Règles :\n"
        "- Réponds UNIQUEMENT en français, ton professionnel mais accessible.\n"
        "- Donne des conseils concrets, structurés en points/bullets.\n"
        "- Tu ne donnes pas de certitude absolue sur l'issue d'un dossier, seulement des "
        "pistes d'amélioration et des orientations vers les bonnes catégories de programmes.\n"
        "- Si une info est incertaine ou peut changer (scores CRS, listes de métiers), "
        "dis-le clairement et renvoie vers les sites officiels.\n"
    )

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": profil_context},
                {
                    "role": "user",
                    "content": f"Question de l'utilisateur concernant son projet de RP :\n{user_message}",
                },
            ],
            temperature=0.4,
        )
        answer = completion.choices[0].message["content"].strip()
    except Exception:
        answer = (
            "Je n'ai pas pu générer de réponse pour l'instant (erreur technique côté serveur). "
            "Réessaie dans quelques minutes ou contacte le support."
        )

    return JsonResponse({"answer": answer})


# -------------------------------------------------------------------
#  GUIDES PROGRAMMES RP (LISTE + DÉTAIL)
# -------------------------------------------------------------------
def program_list_view(request):
    """
    Liste des programmes RP (Canada / Australie) avec filtres simples.
    """
    country_filter = request.GET.get("country")
    category_filter = request.GET.get("category")

    programs = ImmigrationProgram.objects.filter(is_active=True)

    if country_filter in ["CA", "AU"]:
        programs = programs.filter(country=country_filter)

    if category_filter:
        programs = programs.filter(category__iexact=category_filter)

    # Pour les filtres (chips) dans le template
    available_countries = ["CA", "AU"]
    categories = (
        programs.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    context = {
        "programs": programs,
        "selected_country": country_filter,
        "selected_category": category_filter,
        "available_countries": available_countries,
        "categories": categories,
    }
    return render(request, "permanent_residence/program_list.html", context)


def program_detail_view(request, slug):
    """
    Fiche détaillée d’un programme RP :
    - résumé
    - lien officiel
    - ressources (vidéos, captures, articles…)
    """
    program = get_object_or_404(ImmigrationProgram, slug=slug, is_active=True)
    resources = program.resources.all()

    grouped_resources = {}
    for res in resources:
        grouped_resources.setdefault(res.resource_type, []).append(res)

    context = {
        "program": program,
        "grouped_resources": grouped_resources,
    }
    return render(request, "permanent_residence/program_detail.html", context)


# -------------------------------------------------------------------
#  PAGE HTML COACH IA (simple, pour le lien de navigation)
# -------------------------------------------------------------------
@login_required
def coach_view(request):
    """
    Page Coach IA RP (container).
    Pour l’instant, c’est juste une page vitrine qui pourra
    appeler l’API rp_coach_api en AJAX plus tard.
    """
    return render(request, "permanent_residence/coach.html", {})
