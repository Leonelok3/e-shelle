"""
Views pour le module Lebenslauf (CV allemand genere par IA).
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings

from .models import GermanCVProfile, CVExperience, CVEducation, CVLanguage, GeneratedLebenslauf
from .forms import CVProfileForm, CVExperienceForm, CVEducationForm, CVLanguageForm

log = logging.getLogger(__name__)


# ── Prompt systeme IA ─────────────────────────────────────────────────────────
LEBENSLAUF_SYSTEM_PROMPT = """
Tu es un expert RH specialise dans les recrutements Ausbildung en Allemagne.
Tu aides des candidats africains a rediger un Lebenslauf (CV allemand) parfait.

REGLES ABSOLUES DU LEBENSLAUF ALLEMAND :
1. Photo professionnelle (zone reservee si pas de photo)
2. Coordonnees completes : nom, adresse, telephone, email
3. Date de naissance au format DD.MM.YYYY
4. Nationalite mentionnee clairement
5. Parcours professionnel en ordre CHRONOLOGIQUE INVERSE (plus recent en premier)
6. Dates au format MM.YYYY
7. Pas de rubrique "Objectif professionnel"
8. Rubriques standards : Berufserfahrung / Ausbildung / Kenntnisse / Sprachen / Interessen
9. Maximum 2 pages, format DIN A4
10. Langue : ALLEMAND uniquement (sauf la nationalite)

ADAPTE le contenu a l'offre d'Ausbildung ciblee.
Mets en valeur les competences pertinentes pour ce poste specifique.
Si l'experience est dans un secteur different, montre le transfert de competences.

Reponds UNIQUEMENT avec du HTML propre et bien structure (pas de markdown),
utilisant des classes CSS : .lebenslauf, .section-title, .entry, .entry-date,
.entry-content, .skills-grid, .skill-item
"""


@login_required
def dashboard(request):
    """Hub personnel : profil, CV generes, liens rapides."""
    try:
        profile = GermanCVProfile.objects.get(user=request.user)
    except GermanCVProfile.DoesNotExist:
        profile = None

    experiences  = CVExperience.objects.filter(user=request.user)
    educations   = CVEducation.objects.filter(user=request.user)
    languages    = CVLanguage.objects.filter(user=request.user)
    generated    = GeneratedLebenslauf.objects.filter(user=request.user)[:5]

    profile_complete = (
        profile is not None and
        bool(profile.first_name) and
        experiences.exists()
    )

    context = {
        "profile":          profile,
        "experiences":      experiences,
        "educations":       educations,
        "languages":        languages,
        "generated":        generated,
        "profile_complete": profile_complete,
    }
    return render(request, "lebenslauf/dashboard.html", context)


@login_required
def edit_profile(request):
    """Modifier les infos personnelles du candidat."""
    try:
        instance = GermanCVProfile.objects.get(user=request.user)
    except GermanCVProfile.DoesNotExist:
        instance = None

    if request.method == "POST":
        form = CVProfileForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Profil mis a jour avec succes !")
            return redirect("lebenslauf:dashboard")
    else:
        # Pre-remplir avec les infos Django User si nouveau profil
        initial = {}
        if not instance:
            u = request.user
            initial = {
                "first_name": u.first_name,
                "last_name":  u.last_name,
                "email":      u.email,
            }
        form = CVProfileForm(instance=instance, initial=initial)

    return render(request, "lebenslauf/edit_profile.html", {"form": form})


@login_required
def manage_experiences(request):
    """Ajouter / modifier les experiences professionnelles."""
    if request.method == "POST":
        form = CVExperienceForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Experience ajoutee !")
            return redirect("lebenslauf:dashboard")
    else:
        form = CVExperienceForm()

    experiences = CVExperience.objects.filter(user=request.user)
    return render(request, "lebenslauf/manage_experiences.html", {
        "form": form, "experiences": experiences
    })


@login_required
def delete_experience(request, pk):
    exp = get_object_or_404(CVExperience, pk=pk, user=request.user)
    exp.delete()
    return redirect("lebenslauf:dashboard")


@login_required
def manage_education(request):
    if request.method == "POST":
        form = CVEducationForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Formation ajoutee !")
            return redirect("lebenslauf:dashboard")
    else:
        form = CVEducationForm()

    educations = CVEducation.objects.filter(user=request.user)
    return render(request, "lebenslauf/manage_education.html", {
        "form": form, "educations": educations
    })


@login_required
def manage_languages(request):
    if request.method == "POST":
        form = CVLanguageForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Langue ajoutee !")
            return redirect("lebenslauf:dashboard")
    else:
        form = CVLanguageForm()

    languages = CVLanguage.objects.filter(user=request.user)
    return render(request, "lebenslauf/manage_languages.html", {
        "form": form, "languages": languages
    })


@login_required
def generate_lebenslauf(request, offer_pk=None):
    """
    Genere un Lebenslauf adapte a une offre specifique (ou candidature spontanee).
    Appelle GPT-4o et sauvegarde le HTML.
    """
    from germany_opportunities.models import AusbildungOffer

    offer = None
    if offer_pk:
        offer = get_object_or_404(AusbildungOffer, pk=offer_pk)

    try:
        profile = GermanCVProfile.objects.get(user=request.user)
    except GermanCVProfile.DoesNotExist:
        messages.error(request, "Completez d'abord votre profil avant de generer un Lebenslauf.")
        return redirect("lebenslauf:edit_profile")

    if request.method == "POST":
        custom_offer_title   = request.POST.get("custom_offer_title", "")
        custom_offer_company = request.POST.get("custom_offer_company", "")

        experiences = CVExperience.objects.filter(user=request.user)
        educations  = CVEducation.objects.filter(user=request.user)
        languages   = CVLanguage.objects.filter(user=request.user)

        # Construire le contexte candidat
        candidate_context = _build_candidate_context(
            profile, experiences, educations, languages
        )

        # Construire le contexte offre
        if offer:
            offer_context = (
                f"Poste : {offer.title}\n"
                f"Entreprise : {offer.company}\n"
                f"Ville : {offer.city}\n"
                f"Secteur : {offer.get_sector_display()}\n"
                f"Description : {offer.description[:600]}"
            )
        elif custom_offer_title:
            offer_context = (
                f"Poste : {custom_offer_title}\n"
                f"Entreprise : {custom_offer_company}"
            )
        else:
            offer_context = "Candidature spontanee dans le secteur : " + profile.target_sector

        html_content = _call_ai_generate(candidate_context, offer_context)

        if html_content:
            generated = GeneratedLebenslauf.objects.create(
                user=request.user,
                offer=offer,
                custom_offer_title=custom_offer_title,
                custom_offer_company=custom_offer_company,
                content_html=html_content,
            )
            return redirect("lebenslauf:view_lebenslauf", pk=generated.pk)
        else:
            messages.error(request, "Erreur lors de la generation. Reessayez.")

    context = {
        "profile": profile,
        "offer":   offer,
    }
    return render(request, "lebenslauf/generate.html", context)


@login_required
def view_lebenslauf(request, pk):
    """Apercu du Lebenslauf genere."""
    lv = get_object_or_404(GeneratedLebenslauf, pk=pk, user=request.user)
    return render(request, "lebenslauf/view_lebenslauf.html", {"lebenslauf": lv})


@login_required
def download_lebenslauf(request, pk):
    """Telechargement du Lebenslauf en HTML (imprimable)."""
    lv = get_object_or_404(GeneratedLebenslauf, pk=pk, user=request.user)
    response = HttpResponse(lv.content_html, content_type="text/html; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="lebenslauf_{pk}.html"'
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_candidate_context(profile, experiences, educations, languages):
    lines = [
        f"Candidat : {profile.full_name}",
        f"Nationalite : {profile.nationality}",
        f"Date de naissance : {profile.date_of_birth.strftime('%d.%m.%Y') if profile.date_of_birth else 'N/A'}",
        f"Email : {profile.email}",
        f"Telephone : {profile.phone}",
        f"Adresse actuelle : {profile.address}",
        f"Niveau d'allemand : {profile.german_level}",
        f"Certificat Goethe obtenu : {'Oui' if profile.goethe_certified else 'Non'}",
        "",
        "=== EXPERIENCES PROFESSIONNELLES ===",
    ]
    for exp in experiences:
        lines += [
            f"- {exp.title} chez {exp.company} ({exp.city}, {exp.country})",
            f"  Periode : {exp.period_display}",
            f"  Description : {exp.description}",
        ]

    lines += ["", "=== FORMATIONS ==="]
    for edu in educations:
        lines += [
            f"- {edu.degree} — {edu.school} ({edu.city}, {edu.country})",
            f"  {edu.start_year} – {edu.end_year or 'en cours'}",
        ]

    lines += ["", "=== LANGUES ==="]
    for lang in languages:
        cert = f" ({lang.certificate})" if lang.certificate else ""
        lines += [f"- {lang.language} : {lang.proficiency}{cert}"]

    return "\n".join(lines)


def _call_ai_generate(candidate_context: str, offer_context: str) -> str:
    """Appelle GPT-4o pour generer le Lebenslauf en HTML."""
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        log.warning("OPENAI_API_KEY manquant — Lebenslauf non genere")
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": LEBENSLAUF_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"PROFIL CANDIDAT :\n{candidate_context}\n\n"
                    f"OFFRE CIBLEE :\n{offer_context}\n\n"
                    "Genere le Lebenslauf complet en HTML structure avec les classes CSS mentionnees."
                )},
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        log.error(f"Lebenslauf AI generation error: {exc}")
        return ""
