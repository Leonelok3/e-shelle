from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json

from .models import (
    VisaCountry, VisaResource, UserProfile,
    VisaProgress, UserProgress, University,
    CountryAdvice, Scholarship, StudentProfile
)
from .forms import UserProfileForm, StudentProfileForm


# ==========================
# PAGES VISA ÉTUDES
# ==========================

def home(request):
    return render(request, "visaetude/home.html")


################################## profil utilisateur #########################
@login_required
def profile(request):
    user = request.user
    instance, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
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
        "user_is_authenticated": True,
    }
    return render(request, "visaetude/profile.html", context)


################################## profil étudiant #########################
@login_required
def student_profile(request):
    user = request.user
    instance, _ = StudentProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = StudentProfileForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            # progression : étape 1 validée
            progress, _ = UserProgress.objects.get_or_create(user=user)
            if not progress.step_1_profile:
                progress.step_1_profile = True
                progress.save()
    else:
        form = StudentProfileForm(instance=instance)

    context = {
        "form": form,
        "user_is_authenticated": True,
    }
    return render(request, "visaetude/student_profile.html", context)


#################### liste des pays ##########################
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
            {"code": c.slug, "nom": c.name, "short": c.short_label or ""}
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


#################### détail d’un pays ##########################
def country_detail(request, country):
    country_obj = VisaCountry.objects.filter(slug=country, is_active=True).first()

    guides = {
        "canada": "Guide complet pour étudier au Canada...",
        "france": "Détails du visa étudiant France...",
        "usa": "Étudier aux USA...",
        "belgique": "Étudier en Belgique...",
        "allemagne": "Visa étudiant Allemagne...",
        "italie": "Visa étudiant Italie...",
        "chine": "Visa étudiant Chine...",
    }

    if not country_obj and country not in guides:
        return redirect("visaetude:countries_list")

    context = {
        "country": country_obj.name if country_obj else country.capitalize(),
        "country_slug": country,
        "guide": guides.get(country, guides.get("canada", "")),
        "universities": University.objects.filter(country=country_obj) if country_obj else [],
        "advices": CountryAdvice.objects.filter(country=country_obj) if country_obj else [],
        "scholarships": Scholarship.objects.filter(country=country_obj) if country_obj else [],
        "resources": country_obj.resources.all() if country_obj else [],
    }
    return render(request, "visaetude/country_detail.html", context)


#################### roadmap ##########################
def roadmap(request):
    visa_progress = None
    progress_percent = 0
    progress_label = "Étape 1/5"

    if request.user.is_authenticated:
        visa_progress, _ = VisaProgress.objects.get_or_create(user=request.user)
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


#################### coach IA ##########################
def coach_ai(request):
    user = request.user if request.user.is_authenticated else None
    if user:
        progress, _ = UserProgress.objects.get_or_create(user=user)
        if not progress.step_5_coach:
            progress.step_5_coach = True
            progress.save()
    return render(request, "visaetude/coach_ai.html")


def resource_view(request, resource_id):
    r = VisaResource.objects.filter(id=resource_id).first()
    if not r:
        return redirect("visaetude:countries_list")
    return render(request, "visaetude/resource_view.html", {"resource": r})


#################### API coach IA ##########################
@csrf_exempt
def coach_ai_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_message = data.get("message", "").strip()
        if not user_message:
            return JsonResponse({"error": "Message vide"}, status=400)

        # ⚠️ Placeholder IA (à remplacer par ton vrai appel OpenAI)
        bot_reply = "Réponse simulée du Coach IA."
        return JsonResponse({"reply": bot_reply})
    except Exception as e:
        print("Erreur IA:", e)
        return JsonResponse({"error": "Erreur interne"}, status=500)


#################### checklist ##########################
def checklist(request):
    return render(request, "visaetude/checklist.html")


from django.contrib.auth.decorators import login_required
from .forms import StudentProfileForm
from .models import StudentProfile, UserProgress

@login_required
def student_profile(request):
    user = request.user
    instance, _ = StudentProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = StudentProfileForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            progress, _ = UserProgress.objects.get_or_create(user=user)
            if not progress.step_1_profile:
                progress.step_1_profile = True
                progress.save()
    else:
        form = StudentProfileForm(instance=instance)

    return render(request, "visaetude/student_profile.html", {"form": form})
