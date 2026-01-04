from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import VisaCountry, VisaResource, UserProfile
from .forms import UserProfileForm

from .models import VisaCountry, VisaResource, UserProfile, VisaProgress


from .models import VisaCountry, University, CountryAdvice, Scholarship
import json

from django.contrib.auth.decorators import login_required

from .models import VisaProgress
# ==========================
# PAGES VISA ÉTUDES
# ==========================

def home(request):
    return render(request, "visaetude/home.html")

################################## profil #########################
def profile(request):
    user = request.user if request.user.is_authenticated else None
    instance = None

    if user:
        instance, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST" and user:
        form = UserProfileForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            # progression : étape 1 validée
            progress, _ = UserProgress.objects.get_or_create(user=user)
            if not progress.step_1_profile:
                progress.step_1_profile = True
                progress.save()
    else:
        form = UserProfileForm(instance=instance)

    context = {
        "form": form,
        "user_is_authenticated": bool(user),
    }
    return render(request, "visaetude/profile.html", context)


#################### fin profil ##########################

#################### country list ###################""
def countries_list(request):
    user = request.user if request.user.is_authenticated else None
    if user:
        progress, _ = UserProgress.objects.get_or_create(user=user)
        if not progress.step_2_country:
            progress.step_2_country = True
            progress.save()

    db_countries = list(VisaCountry.objects.filter(is_active=True))

    if db_countries:
        countries = [
            {
                "code": c.slug,
                "nom": c.name,
                "short": c.short_label or "",
            }
            for c in db_countries
        ]
    else:
        countries = [
            {"code": "canada", "nom": "Canada", "short": ""},
            {"code": "france", "nom": "France", "short": ""},
            {"code": "belgique", "nom": "Belgique", "short": ""},
            {"code": "usa", "nom": "États-Unis", "short": ""},
            {"code": "allemagne", "nom": "Allemagne", "short": ""},
            {"code": "italie", "nom": "Italie", "short": ""},
            {"code": "chine", "nom": "Chine", "short": ""},
        ]

    return render(request, "visaetude/countries_list.html", {"countries": countries})

##################### fin country list #############################



def country_detail(request, country):
    # Récupération du pays à partir du modèle VisaCountry
    country_obj = VisaCountry.objects.filter(slug=country, is_active=True).first()

    # Dictionnaire des guides pour chaque pays (texte de base)
    guides = {
        "canada": "Guide complet pour étudier au Canada...",
        "france": "Détails du visa étudiant France...",
        "usa": "Étudier aux USA...",
        "belgique": "Étudier en Belgique...",
        "allemagne": "Visa étudiant Allemagne...",
        "italie": "Visa étudiant Italie...",
        "chine": "Visa étudiant Chine...",
    }

    # Si le pays n'existe pas dans la base de données ou dans le guide, rediriger vers la liste des pays
    if not country_obj and country not in guides:
        return redirect("visaetude:countries_list")

    # Nom et texte du guide basé sur le pays
    country_name = country_obj.name if country_obj else country.capitalize()
    guide_text = guides.get(country, guides.get("canada", ""))

    # Récupérer les universités disponibles pour ce pays
    universities = University.objects.filter(country=country_obj) if country_obj else []

    # Récupérer les conseils pour ce pays (par exemple: documents nécessaires, inscription Campus France, etc.)
    advices = CountryAdvice.objects.filter(country=country_obj) if country_obj else []

    # Récupérer les bourses disponibles pour ce pays
    scholarships = Scholarship.objects.filter(country=country_obj) if country_obj else []

    # Récupérer toutes les ressources (vidéos, captures, guides) liées à ce pays
    resources = country_obj.resources.all() if country_obj else []

    # Passer toutes ces informations à la page de rendu
    context = {
        "country": country_name,
        "country_slug": country,
        "guide": guide_text,  # Texte du guide pour le pays
        "universities": universities,  # Liste des universités
        "advices": advices,  # Liste des conseils
        "scholarships": scholarships,  # Liste des bourses
        "resources": resources,  # Ressources pour le pays
    }

    return render(request, "visaetude/country_detail.html", context)



from django.shortcuts import render
from .models import VisaProgress


def roadmap(request):
    """
    Page Plan d’action Visa Études
    - Fonctionne pour utilisateurs connectés et anonymes
    - Ne casse jamais le template
    """

    visa_progress = None
    progress_percent = 0
    progress_label = "Étape 1/5"

    if request.user.is_authenticated:
        visa_progress, _ = VisaProgress.objects.get_or_create(
            user=request.user
        )

        total_steps = 5
        completed_steps = visa_progress.completed_steps
        progress_percent = int((completed_steps / total_steps) * 100)
        progress_label = f"Étape {visa_progress.current_stage}/{total_steps}"

    return render(
        request,
        "visaetude/roadmap.html",
        {
            "visa_progress": visa_progress,
            "visa_progress_percent": progress_percent,
            "visa_progress_label": progress_label,
        },
    )



##################### fin checklist #####################

################## def coach_ai #################

def coach_ai(request):
    user = request.user if request.user.is_authenticated else None
    if user:
        progress, _ = UserProgress.objects.get_or_create(user=user)
        if not progress.step_5_coach:
            progress.step_5_coach = True
            progress.save()

    return render(request, "visaetude/coach_ai.html")

#{}######################### fin def coach_ai #########""
def resource_view(request, resource_id):
    r = VisaResource.objects.filter(id=resource_id).first()
    if not r:
        return redirect("visaetude:countries_list")
    return render(request, "visaetude/resource_view.html", {"resource": r})


# ==========================
# API COACH IA (FAUSSE RÉPONSE POUR L’INSTANT)
# ==========================

@csrf_exempt
def coach_ai_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse({"error": "Message vide"}, status=400)

        response = openai.ChatCompletion.create(
            model="gpt-4.1-mini",
            messages=[{"role": "system", "content": "Tu es un expert en immigration et visas étudiants."},
                      {"role": "user", "content": user_message}],
            max_tokens=700,
            temperature=0.4,
        )

        bot_reply = response["choices"][0]["message"]["content"]
        return JsonResponse({"reply": bot_reply})

    except Exception as e:
        print("Erreur IA:", e)
        return JsonResponse({"error": "Erreur interne"}, status=500)


def checklist(request):
    # Ici tu retournes ta vue pour la checklist, par exemple:
    return render(request, "visaetude/checklist.html")