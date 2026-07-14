import logging
import io
import re
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .models import CanadaCVProfile, CanadaCVExperience, CanadaCVEducation, CanadaCVLanguage, GeneratedCanadaResume
from .forms import CanadaCVProfileForm, CanadaCVExperienceForm, CanadaCVEducationForm, CanadaCVLanguageForm
from jobs.models import CanadaJobOffer

log = logging.getLogger(__name__)

def check_user_has_paid_edu_subscription(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if hasattr(user, "profile") and user.profile.plan in ["pro", "enterprise"]:
        return True
    try:
        from accounts.models import AppSubscription
        sub = AppSubscription.get_active_for_user(user, "edu")
        if sub and sub.is_active and not sub.plan.is_free:
            return True
    except Exception:
        pass
    return False


@login_required
def dashboard(request):
    try:
        profile = CanadaCVProfile.objects.get(user=request.user)
    except CanadaCVProfile.DoesNotExist:
        profile = None

    experiences = CanadaCVExperience.objects.filter(user=request.user)
    educations = CanadaCVEducation.objects.filter(user=request.user)
    languages = CanadaCVLanguage.objects.filter(user=request.user)
    generated = GeneratedCanadaResume.objects.filter(user=request.user)[:5]

    profile_complete = (
        profile is not None and
        bool(profile.first_name) and
        experiences.exists()
    )

    context = {
        "profile": profile,
        "experiences": experiences,
        "educations": educations,
        "languages": languages,
        "generated": generated,
        "profile_complete": profile_complete,
        "is_pro": check_user_has_paid_edu_subscription(request.user),
    }
    return render(request, "canada_resume/dashboard.html", context)


@login_required
def edit_profile(request):
    try:
        instance = CanadaCVProfile.objects.get(user=request.user)
    except CanadaCVProfile.DoesNotExist:
        instance = None

    if request.method == "POST":
        form = CanadaCVProfileForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Votre profil a été enregistré avec succès !")
            return redirect("canada_resume:dashboard")
    else:
        initial = {}
        if not instance:
            u = request.user
            initial = {
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
            }
        form = CanadaCVProfileForm(instance=instance, initial=initial)

    return render(request, "canada_resume/edit_profile.html", {"form": form})


@login_required
def manage_experiences(request):
    if request.method == "POST":
        form = CanadaCVExperienceForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Expérience professionnelle ajoutée !")
            return redirect("canada_resume:dashboard")
    else:
        form = CanadaCVExperienceForm()

    experiences = CanadaCVExperience.objects.filter(user=request.user)
    return render(request, "canada_resume/manage_experiences.html", {
        "form": form, "experiences": experiences
    })


@login_required
def delete_experience(request, pk):
    exp = get_object_or_404(CanadaCVExperience, pk=pk, user=request.user)
    exp.delete()
    messages.success(request, "Expérience supprimée.")
    return redirect("canada_resume:dashboard")


@login_required
def manage_education(request):
    if request.method == "POST":
        form = CanadaCVEducationForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Formation académique ajoutée !")
            return redirect("canada_resume:dashboard")
    else:
        form = CanadaCVEducationForm()

    educations = CanadaCVEducation.objects.filter(user=request.user)
    return render(request, "canada_resume/manage_education.html", {
        "form": form, "educations": educations
    })


@login_required
def delete_education(request, pk):
    edu = get_object_or_404(CanadaCVEducation, pk=pk, user=request.user)
    edu.delete()
    messages.success(request, "Formation supprimée.")
    return redirect("canada_resume:dashboard")


@login_required
def manage_languages(request):
    if request.method == "POST":
        form = CanadaCVLanguageForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Compétence linguistique ajoutée !")
            return redirect("canada_resume:dashboard")
    else:
        form = CanadaCVLanguageForm()

    languages = CanadaCVLanguage.objects.filter(user=request.user)
    return render(request, "canada_resume/manage_languages.html", {
        "form": form, "languages": languages
    })


@login_required
def delete_language(request, pk):
    lang = get_object_or_404(CanadaCVLanguage, pk=pk, user=request.user)
    lang.delete()
    messages.success(request, "Compétence linguistique supprimée.")
    return redirect("canada_resume:dashboard")


@login_required
def generate_resume(request, offer_pk=None):
    offer = None
    if offer_pk:
        offer = get_object_or_404(CanadaJobOffer, pk=offer_pk)

    try:
        profile = CanadaCVProfile.objects.get(user=request.user)
    except CanadaCVProfile.DoesNotExist:
        messages.error(request, "Veuillez d'abord compléter votre profil avant de pouvoir générer un CV.")
        return redirect("canada_resume:edit_profile")

    if request.method == "POST":
        custom_offer_title = request.POST.get("custom_offer_title", "")
        custom_offer_company = request.POST.get("custom_offer_company", "")
        lang_choice = request.POST.get("language", "fr")

        experiences = CanadaCVExperience.objects.filter(user=request.user)
        educations = CanadaCVEducation.objects.filter(user=request.user)
        languages = CanadaCVLanguage.objects.filter(user=request.user)

        candidate_context = _build_candidate_context(profile, experiences, educations, languages)

        if offer:
            offer_context = (
                f"Poste : {offer.title}\n"
                f"Entreprise : {offer.company}\n"
                f"Lieu : {offer.city}, {offer.province}\n"
                f"Description : {offer.description}"
            )
        elif custom_offer_title:
            offer_context = (
                f"Poste : {custom_offer_title}\n"
                f"Entreprise : {custom_offer_company}"
            )
        else:
            offer_context = f"Candidature spontanée dans le secteur : {profile.target_sector}"

        html_content, cover_letter = _call_ai_generate_canada(candidate_context, offer_context, lang_choice)

        if html_content:
            generated = GeneratedCanadaResume.objects.create(
                user=request.user,
                offer=offer,
                custom_offer_title=custom_offer_title,
                custom_offer_company=custom_offer_company,
                language=lang_choice,
                content_html=html_content,
                ai_cover_letter=cover_letter,
            )
            return redirect("canada_resume:view_resume", pk=generated.pk)
        else:
            messages.error(request, "Une erreur est survenue lors de la génération. Veuillez réessayer.")

    context = {
        "profile": profile,
        "offer": offer,
    }
    return render(request, "canada_resume/generate.html", context)


@login_required
def view_resume(request, pk):
    resume = get_object_or_404(GeneratedCanadaResume, pk=pk, user=request.user)
    return render(request, "canada_resume/view_resume.html", {
        "resume": resume,
        "is_pro": check_user_has_paid_edu_subscription(request.user),
    })


@login_required
def download_resume_docx(request, pk):
    if not check_user_has_paid_edu_subscription(request.user):
        messages.warning(request, "Le téléchargement du CV au format Word (.docx) est réservé aux abonnés Premium.")
        return redirect("canada_resume:dashboard")

    resume = get_object_or_404(GeneratedCanadaResume, pk=pk, user=request.user)
    doc = Document()

    # Configuration des marges
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Nettoyage et extraction de texte depuis HTML généré pour le CV
    clean_html = re.sub(r'<style[^>]*>.*?</style>', '', resume.content_html, flags=re.DOTALL)
    clean_html = re.sub(r'<script[^>]*>.*?</script>', '', clean_html, flags=re.DOTALL)
    
    # Remplacement simple des balises HTML pour docx
    from html.parser import HTMLParser

    class SimpleDocxParser(HTMLParser):
        def __init__(self, document):
            super().__init__()
            self.doc = document
            self.current_paragraph = None
            self.current_tag = None

        def handle_starttag(self, tag, attrs):
            self.current_tag = tag
            if tag in ('h1', 'h2', 'h3'):
                self.current_paragraph = self.doc.add_paragraph()
                self.current_paragraph.paragraph_format.space_before = Pt(12)
                self.current_paragraph.paragraph_format.space_after = Pt(4)
                self.current_paragraph.paragraph_format.keep_with_next = True
            elif tag in ('p', 'div'):
                self.current_paragraph = self.doc.add_paragraph()
                self.current_paragraph.paragraph_format.space_after = Pt(6)
            elif tag == 'li':
                self.current_paragraph = self.doc.add_paragraph(style='List Bullet')
                self.current_paragraph.paragraph_format.space_after = Pt(2)
                self.current_paragraph.paragraph_format.left_indent = Inches(0.25)
            elif tag == 'br':
                if self.current_paragraph:
                    self.current_paragraph.add_run('\n')

        def handle_endtag(self, tag):
            self.current_tag = None

        def handle_data(self, data):
            text = data.strip()
            if not text:
                return
            if self.current_tag in ('h1', 'h2', 'h3'):
                run = self.current_paragraph.add_run(text)
                run.bold = True
                if self.current_tag == 'h1':
                    run.font.size = Pt(16)
                    self.current_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    run.font.size = Pt(12)
                    run.font.color.rgb = RGBColor(16, 43, 78) # Dark Blue #102B4E
            elif self.current_paragraph:
                run = self.current_paragraph.add_run(" " + text if self.current_paragraph.runs else text)
                run.font.size = Pt(10)
                run.font.name = 'Calibri'
                if self.current_tag == 'strong':
                    run.bold = True

    parser = SimpleDocxParser(doc)
    parser.feed(clean_html)

    # Génération du flux
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    filename = f"cv_canada_{pk}.docx"
    response = HttpResponse(
        file_stream.read(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def download_cover_letter_docx(request, pk):
    if not check_user_has_paid_edu_subscription(request.user):
        messages.warning(request, "Le téléchargement de la lettre de motivation est réservé aux abonnés Premium.")
        return redirect("canada_resume:dashboard")

    resume = get_object_or_404(GeneratedCanadaResume, pk=pk, user=request.user)
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    if resume.ai_cover_letter:
        for line in resume.ai_cover_letter.split('\n'):
            cleaned_line = line.strip()
            if not cleaned_line:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(6)
                continue

            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.line_spacing = 1.15
            
            parts = re.split(r'(\*\*.*?\*\*)', cleaned_line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    run = p.add_run(part[2:-2])
                    run.bold = True
                else:
                    p.add_run(part)

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    filename = f"lettre_motivation_canada_{pk}.docx"
    response = HttpResponse(
        file_stream.read(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _build_candidate_context(profile, experiences, educations, languages):
    lines = [
        f"Nom complet : {profile.full_name}",
        f"Email : {profile.email}",
        f"Téléphone : {profile.phone}",
        f"Adresse : {profile.address}",
        f"LinkedIn : {profile.linkedin}",
        f"Secteur d'activité ciblé : {profile.target_sector}",
        f"Provinces acceptées au Canada : {profile.target_provinces}",
        "",
        "=== EXPÉRIENCES PROFESSIONNELLES ===",
    ]
    for exp in experiences:
        lines += [
            f"- {exp.title} chez {exp.company} ({exp.city}, {exp.province_country})",
            f"  Période : {exp.period_display_fr}",
            f"  Description & Réalisations : {exp.description}",
        ]

    lines += ["", "=== FORMATIONS ==="]
    for edu in educations:
        lines += [
            f"- {edu.degree} — {edu.school} ({edu.city}, {edu.province_country})",
            f"  Années : {edu.start_year} – {edu.end_year or 'Présent'}",
        ]

    lines += ["", "=== LANGUES ==="]
    for lang in languages:
        cert = f" ({lang.certificate})" if lang.certificate else ""
        lines += [f"- {lang.language} : {lang.proficiency}{cert}"]

    return "\n".join(lines)


def _call_ai_generate_canada(candidate_context: str, offer_context: str, lang_choice: str) -> tuple[str, str]:
    import datetime
    from ai_engine.services.llm_service import call_llm

    today_str = datetime.date.today().strftime("%d/%m/%Y")

    if lang_choice == "en":
        system_prompt = (
            "You are an expert HR recruiter specializing in Canadian immigration and ATS-friendly resumes.\n"
            "Your task is to generate two professional documents in English for the candidate:\n"
            "1. An ATS-friendly Canadian resume (HTML format).\n"
            "2. A compelling Canadian cover letter (Text format).\n\n"
            "CRITICAL CANADIAN RESUME AND COVER LETTER RULES:\n"
            "- NO photo. Never include or leave a placeholder for a photo.\n"
            "- NO birth date, age, marital status, gender, or nationality. Including these is illegal in Canada and causes ATS rejection.\n"
            "- Focus on quantitative accomplishments, action verbs, and transferable skills matched to the target job description.\n"
            "- Use clean single-column format for the HTML layout with standard headings: SUMMARY, EXPERIENCE, EDUCATION, SKILLS.\n"
            "- The Cover Letter must start with candidate coordinates, date, employer details (or general hiring team), subject line in bold (using **), body text, and closing (Sincerely, [Candidate Name]).\n\n"
            "RESPONSE FORMAT:\n"
            "Output the raw HTML for the resume first. Do not wrap in ```html block.\n"
            "Then output the divider exactly:\n"
            "=== ANSCHREIBEN_START ===\n"
            "Then output the plain text cover letter."
        )
    else:
        system_prompt = (
            "Tu es un expert en recrutement canadien spécialisé dans l'immigration et la rédaction de CV compatibles ATS.\n"
            "Ta tâche est de générer deux documents professionnels en Français canadien pour le candidat :\n"
            "1. Un CV au format canadien compatible ATS (format HTML).\n"
            "2. Une lettre de présentation / motivation convaincante (format Texte).\n\n"
            "RÈGLES CRITIQUES DU FORMAT CANADIEN :\n"
            "- AUCUNE photo. Ne jamais inclure de photo ni de zone réservée pour une photo.\n"
            "- AUCUNE mention de l'âge, date de naissance, genre, statut marital ou nationalité (Interdit par les lois canadiennes sur les droits de la personne).\n"
            "- CV rédigé en colonne simple, propre et lisible avec des rubriques standards : PROFIL, EXPÉRIENCE PROFESSIONNELLE, FORMATION, COMPÉTENCES.\n"
            "- Valorise les compétences transférables, utilise des verbes d'action et présente des réalisations chiffrées/concrètes.\n"
            "- La Lettre de Motivation doit débuter par les coordonnées, la date, l'adresse de l'employeur (ou recrutement), la ligne d'objet en gras (avec **), le corps du texte et la formule de politesse finale (Cordialement, [Nom du Candidat]).\n\n"
            "FORMAT DE LA RÉPONSE :\n"
            "Génère d'abord le code HTML brut du CV. Pas de bloc ```html.\n"
            "Insère ensuite exactement le délimiteur :\n"
            "=== ANSCHREIBEN_START ===\n"
            "Génère ensuite la lettre de motivation en format texte brut."
        )

    user_prompt = (
        f"PROFIL DU CANDIDAT :\n{candidate_context}\n\n"
        f"OFFRE D'EMPLOI CIBLEE :\n{offer_context}\n\n"
        f"Date du jour : {today_str}\n\n"
        "Génère maintenant le CV canadien (HTML) et la lettre de motivation."
    )

    try:
        response = call_llm(system_prompt, user_prompt)
        if not response:
            return "", ""

        response = response.replace("```html", "").replace("```", "").strip()

        if "=== ANSCHREIBEN_START ===" in response:
            parts = response.split("=== ANSCHREIBEN_START ===")
            html_content = parts[0].strip()
            cover_letter = parts[1].strip()
        else:
            html_content = response
            cover_letter = ""

        return html_content, cover_letter
    except Exception as exc:
        log.error(f"Canada CV generation error: {exc}")
        return "", ""


@login_required
def improve_description_api(request):
    """
    Appelle Gemini pour réécrire la description de poste brute saisie par l'utilisateur
    au format canadien professionnel compatible ATS (verbes d'action, puces).
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Méthode non autorisée."})

    import json
    try:
        data = json.loads(request.body)
        raw_text = data.get("text", "").strip()
    except Exception:
        raw_text = request.POST.get("text", "").strip()

    if not raw_text:
        return JsonResponse({"success": False, "error": "Veuillez saisir une description à améliorer."})

    from ai_engine.services.llm_service import call_llm

    system_prompt = (
        "Tu es un expert RH canadien. Transforme la description de tâche brute fournie "
        "en une liste à puces (bullet points) professionnelle de 3 à 5 éléments, en commençant par des verbes d'action à l'infinitif "
        "(ex: 'Gérer...', 'Assurer...', 'Collaborer...', 'Optimiser...'). Rends le contenu extrêmement professionnel "
        "et adapté pour passer les filtres ATS. Ne mets aucune introduction, salutation ou conclusion, commence directement par les puces."
    )

    try:
        improved_text = call_llm(system_prompt, f"Description brute :\n{raw_text}")
        if improved_text:
            return JsonResponse({"success": True, "improved_text": improved_text.strip()})
        return JsonResponse({"success": False, "error": "L'IA a retourné une réponse vide."})
    except Exception as e:
        log.error(f"Error in improve_description_api: {e}")
        return JsonResponse({"success": False, "error": str(e)})

