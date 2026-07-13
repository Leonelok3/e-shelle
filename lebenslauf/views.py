"""
Views pour le module Lebenslauf (CV allemand genere par IA).
"""
import logging
from html.parser import HTMLParser
from docx import Document
from docx.shared import Pt, Inches, RGBColor
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

        html_content, cover_letter = _call_ai_generate(candidate_context, offer_context)

        if html_content:
            generated = GeneratedLebenslauf.objects.create(
                user=request.user,
                offer=offer,
                custom_offer_title=custom_offer_title,
                custom_offer_company=custom_offer_company,
                content_html=html_content,
                ai_cover_letter=cover_letter,
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


class DocxHTMLParser(HTMLParser):
    def __init__(self, doc):
        super().__init__()
        self.doc = doc
        self.current_tag = None
        self.current_paragraph = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in ('h1', 'h2', 'h3', 'h4'):
            self.current_paragraph = self.doc.add_paragraph()
            self.current_paragraph.paragraph_format.space_before = Pt(12)
            self.current_paragraph.paragraph_format.space_after = Pt(6)
        elif tag in ('p', 'div'):
            self.current_paragraph = self.doc.add_paragraph()
            self.current_paragraph.paragraph_format.space_after = Pt(6)
        elif tag == 'li':
            self.current_paragraph = self.doc.add_paragraph(style='List Bullet')
            self.current_paragraph.paragraph_format.space_after = Pt(3)
        elif tag == 'br':
            if self.current_paragraph:
                self.current_paragraph.add_run('\n')
                
    def handle_endtag(self, tag):
        self.current_tag = None
        
    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self.current_tag in ('h1', 'h2', 'h3', 'h4'):
            run = self.current_paragraph.add_run(text)
            run.bold = True
            if self.current_tag == 'h1':
                run.font.size = Pt(18)
                run.font.color.rgb = RGBColor(45, 55, 72)  # Slate Gray
            elif self.current_tag == 'h2':
                run.font.size = Pt(13)
                run.font.color.rgb = RGBColor(227, 0, 15)  # German Red
            else:
                run.font.size = Pt(11)
        elif self.current_paragraph:
            self.current_paragraph.add_run(" " + text if self.current_paragraph.runs else text)


@login_required
def download_lebenslauf_docx(request, pk):
    """Téléchargement du CV et de la Lettre de motivation au format Word (.docx)."""
    import io
    import re

    lv = get_object_or_404(GeneratedLebenslauf, pk=pk, user=request.user)
    
    doc = Document()
    
    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # 1. Add Cover Letter (Anschreiben) if it exists
    if lv.ai_cover_letter:
        p_title = doc.add_paragraph()
        run_title = p_title.add_run("BEWERBUNGSSCHREIBEN (ANSCHREIBEN)")
        run_title.bold = True
        run_title.font.size = Pt(14)
        p_title.paragraph_format.space_after = Pt(12)
        
        # Add the body of the cover letter
        for line in lv.ai_cover_letter.split('\n'):
            cleaned_line = line.strip()
            p = doc.add_paragraph(cleaned_line)
            p.paragraph_format.space_after = Pt(6)
            
        doc.add_page_break()

    # 2. Add CV (Lebenslauf) HTML
    p_cv_title = doc.add_paragraph()
    run_cv_title = p_cv_title.add_run("LEBENSLAUF")
    run_cv_title.bold = True
    run_cv_title.font.size = Pt(14)
    p_cv_title.paragraph_format.space_after = Pt(12)

    # Strip style and script tags to prevent parsing errors
    clean_html = re.sub(r'<style[^>]*>.*?</style>', '', lv.content_html, flags=re.DOTALL)
    clean_html = re.sub(r'<script[^>]*>.*?</script>', '', clean_html, flags=re.DOTALL)

    parser = DocxHTMLParser(doc)
    parser.feed(clean_html)

    # Save to memory stream
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    filename = f"bewerbung_{pk}.docx"
    response = HttpResponse(
        file_stream.read(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
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


def _call_ai_generate(candidate_context: str, offer_context: str) -> tuple[str, str]:
    """
    Appelle Gemini pour générer à la fois le Lebenslauf en HTML et la lettre de motivation (Anschreiben)
    en un seul appel pour des raisons de performance et pour éviter le timeout.
    """
    from ai_engine.services.llm_service import call_llm

    system_prompt = (
        "Du bist ein renommierter deutscher HR-Experte, spezialisiert auf das deutsche Bewerbungsverfahren.\n"
        "Deine Aufgabe ist es, für den Kandidaten zwei Dokumente in fehlerfreiem, professionellem Deutsch zu erstellen:\n"
        "1. Einen modernen, professionellen Lebenslauf (CV) im zweiseitigen/zweispaltigen Tabellen-Layout (HTML).\n"
        "2. Ein überzeugendes Anschreiben (Bewerbungsschreiben) nach DIN 5008 (Text).\n\n"
        "Übersetze alle Informationen des Kandidaten auf Deutsch und formuliere seine Erfahrungen so um, dass die "
        "übertragbaren Kompetenzen (Pünktlichkeit, Organisation, Empathie) für das Ziel-Ausbildungsangebot im Vordergrund stehen.\n\n"
        "REGLEN FÜR DAS HTML-LAYOUT DES LEBENSLAUFS:\n"
        "- Generiere einen Container mit zwei Spalten: linke Spalte dunkelgrau (#2D3748) für persönliche Daten & Sprachen, "
        "rechte Spalte weiß für Lebenslauf, Berufserfahrung, Ausbildung, Kenntnisse.\n"
        "- Verwende Flexbox/Grid mit Inlinestilen.\n"
        "- Nutze das deutsche Datumsformat (MM.YYYY).\n\n"
        "REGLEN FÜR DAS ANSCHREIBEN:\n"
        "- Formale Struktur nach DIN 5008 (Absender, Empfänger, Datum, Betreff, Anrede, Einleitung, Hauptteil, Schluss, Grußformel).\n"
        "- Verbinde die Erfahrungen des Kandidaten mit dem Angebot. Zeige seine Motivation, nach Deutschland zu kommen.\n\n"
        "FORMATIERUNG DER ANTWORT:\n"
        "Gib zuerst den reinen HTML-Code des Lebenslaufs aus. Kein Markdown (kein ```html).\n"
        "Füge danach die genaue Trennzeile ein:\n"
        "=== ANSCHREIBEN_START ===\n"
        "Gib danach den reinen Text des Anschreibens aus."
    )

    user_prompt = (
        f"KANDIDATENPROFIL:\n{candidate_context}\n\n"
        f"ZIELSTELLENANGEBOT:\n{offer_context}\n\n"
        "Erstelle jetzt den Lebenslauf (HTML) und das Anschreiben (Text)."
    )

    try:
        response = call_llm(system_prompt, user_prompt)
        if not response:
            return "", ""

        # Clean markdown code blocks if any
        response = response.replace("```html", "").replace("```", "").strip()

        if "=== ANSCHREIBEN_START ===" in response:
            parts = response.split("=== ANSCHREIBEN_START ===")
            html_content = parts[0].strip()
            cover_letter = parts[1].strip()
        else:
            # Fallback if delimiter not found
            html_content = response
            cover_letter = ""

        return html_content, cover_letter
    except Exception as exc:
        log.error(f"Lebenslauf AI generation error: {exc}")
        return "", ""
