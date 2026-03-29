from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
import json

from .models import (
    VisaCountry, VisaResource, UserProfile,
    VisaProgress, UserProgress, University,
    CountryAdvice, Scholarship, StudentProfile
)
from .forms import UserProfileForm, StudentProfileForm
from billing.services import has_candidate_access


# ── Helper paywall ──────────────────────────────────────────────
def _require_premium(request):
    """
    Retourne None si l'accès est OK, sinon un redirect vers billing:pricing.
    Usage : resp = _require_premium(request); if resp: return resp
    """
    if not request.user.is_authenticated:
        return redirect(f"{reverse('authentification:login')}?next={request.path}")
    if not has_candidate_access(request.user):
        messages.error(
            request,
            "🔒 Cette fonctionnalité est réservée aux abonnés Premium. "
            "Accédez à toutes les ressources pour 6 500 XAF/mois."
        )
        return redirect(f"{reverse('billing:pricing')}?next={request.path}")
    return None


# ── PAGES GRATUITES ─────────────────────────────────────────────

def home(request):
    return render(request, "visaetude/home.html")


def countries_list(request):
    """Liste des pays — GRATUIT (vitrine)."""
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
            {"code": "canada",    "nom": "Canada",       "short": ""},
            {"code": "france",    "nom": "France",        "short": ""},
            {"code": "belgique",  "nom": "Belgique",      "short": ""},
            {"code": "usa",       "nom": "États-Unis",    "short": ""},
            {"code": "allemagne", "nom": "Allemagne",     "short": ""},
            {"code": "italie",    "nom": "Italie",        "short": ""},
            {"code": "chine",     "nom": "Chine",         "short": ""},
        ]

    has_premium = request.user.is_authenticated and has_candidate_access(request.user)
    return render(request, "visaetude/countries_list.html", {
        "countries": countries,
        "has_premium": has_premium,
    })


# ── PAGES PREMIUM ────────────────────────────────────────────────

@login_required
def student_profile(request):
    """Profil étudiant — PREMIUM."""
    gate = _require_premium(request)
    if gate:
        return gate

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
            messages.success(request, "✅ Profil étudiant enregistré.")
    else:
        form = StudentProfileForm(instance=instance)

    return render(request, "visaetude/student_profile.html", {
        "form": form,
        "user_is_authenticated": True,
    })


@login_required
def profile(request):
    """Profil visa de base — PREMIUM."""
    gate = _require_premium(request)
    if gate:
        return gate

    user = request.user
    instance, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            progress, _ = UserProgress.objects.get_or_create(user=user)
            if not progress.step_1_profile:
                progress.step_1_profile = True
                progress.save()
    else:
        form = UserProfileForm(instance=instance)

    return render(request, "visaetude/profile.html", {
        "form": form,
        "user_is_authenticated": True,
    })


def country_detail(request, country):
    """Détail d'un pays — PREMIUM pour le contenu complet."""
    country_obj = VisaCountry.objects.filter(slug=country, is_active=True).first()

    guides = {
        "canada":    "Guide complet pour étudier au Canada...",
        "france":    "Détails du visa étudiant France...",
        "usa":       "Étudier aux USA...",
        "belgique":  "Étudier en Belgique...",
        "allemagne": "Visa étudiant Allemagne...",
        "italie":    "Visa étudiant Italie...",
        "chine":     "Visa étudiant Chine...",
    }

    if not country_obj and country not in guides:
        return redirect("visaetude:countries_list")

    has_premium = request.user.is_authenticated and has_candidate_access(request.user)

    context = {
        "country": country_obj.name if country_obj else country.capitalize(),
        "country_slug": country,
        "guide": guides.get(country, guides.get("canada", "")),
        "universities": University.objects.filter(country=country_obj) if (country_obj and has_premium) else [],
        "advices": CountryAdvice.objects.filter(country=country_obj) if (country_obj and has_premium) else [],
        "scholarships": Scholarship.objects.filter(country=country_obj) if (country_obj and has_premium) else [],
        "resources": country_obj.resources.all() if (country_obj and has_premium) else [],
        "has_premium": has_premium,
    }
    return render(request, "visaetude/country_detail.html", context)


def roadmap(request):
    """Parcours visa — PREMIUM."""
    gate = _require_premium(request)
    if gate:
        return gate

    visa_progress, _ = VisaProgress.objects.get_or_create(user=request.user)
    total_steps = 5
    completed_steps = visa_progress.completed_steps
    progress_percent = int((completed_steps / total_steps) * 100)
    progress_label = f"Étape {visa_progress.current_stage}/{total_steps}"

    return render(request, "visaetude/roadmap.html", {
        "visa_progress": visa_progress,
        "visa_progress_percent": progress_percent,
        "visa_progress_label": progress_label,
    })


def checklist(request):
    """Checklist documents — PREMIUM."""
    gate = _require_premium(request)
    if gate:
        return gate
    return render(request, "visaetude/checklist.html")


def coach_ai(request):
    """Coach IA — PREMIUM."""
    gate = _require_premium(request)
    if gate:
        return gate

    if request.user.is_authenticated:
        progress, _ = UserProgress.objects.get_or_create(user=request.user)
        if not progress.step_5_coach:
            progress.step_5_coach = True
            progress.save()

    return render(request, "visaetude/coach_ai.html")


def resource_view(request, resource_id):
    """Ressource individuelle — PREMIUM."""
    gate = _require_premium(request)
    if gate:
        return gate

    r = VisaResource.objects.filter(id=resource_id).first()
    if not r:
        return redirect("visaetude:countries_list")
    return render(request, "visaetude/resource_view.html", {"resource": r})


# ── API Coach IA ─────────────────────────────────────────────────

@csrf_exempt
def coach_ai_api(request):
    """API Coach IA — PREMIUM (vérifié côté API aussi)."""
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    if not request.user.is_authenticated or not has_candidate_access(request.user):
        return JsonResponse({"error": "Abonnement Premium requis."}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_message = data.get("message", "").strip()
        if not user_message:
            return JsonResponse({"error": "Message vide"}, status=400)

        # Placeholder IA — à brancher sur OpenAI
        bot_reply = (
            "Je suis le Coach IA Immigration97. Pour une réponse personnalisée, "
            "posez votre question sur votre destination et votre situation."
        )
        return JsonResponse({"reply": bot_reply})
    except Exception as e:
        return JsonResponse({"error": "Erreur interne"}, status=500)
