# cv_generator/views.py
import json
import logging
import re
from io import BytesIO

from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.text import slugify

from xhtml2pdf import pisa

from .models import (
    CV, CVTemplate, Experience, Education,
    Skill, Language, Volunteer, Hobby,
    Certification, Project, CVExportHistory
)
from .forms import (
    Step1Form, Step3Form, ExperienceForm,
    EducationForm, SkillForm, LanguageForm, VolunteerForm,
    HobbyForm, CertificationForm, ProjectForm
)

logger = logging.getLogger(__name__)

# Optionnel: service IA si présent
try:
    from .services.openai_service import OpenAIService
    _ai_service = OpenAIService()
except Exception as _e:
    logger.info("OpenAIService indisponible ou non configuré: %s", _e)
    _ai_service = None


# ---------------------------
# Helpers généraux
# ---------------------------
def _safe_manager_list(obj, attr_name):
    """
    Retourne list(obj.<attr>.all()) si possible, sinon [].
    Evite l'AttributeError si la relation n'existe pas.
    """
    mgr = getattr(obj, attr_name, None)
    if mgr is None:
        return []
    try:
        if hasattr(mgr, "all"):
            return list(mgr.all())
    except Exception:
        pass
    # pas de manager, retourne vide
    return []


def _cv_context(cv, step, **extra):
    """Contexte standardisé pour create_cv.html — tolérant aux absences de relations."""
    base = {
        "cv": cv,
        "current_step": step,
        "experiences": _safe_manager_list(cv, "experiences"),
        "educations": _safe_manager_list(cv, "education_set"),
        "skills": _safe_manager_list(cv, "skills"),
        "languages": _safe_manager_list(cv, "languages"),
        "certifications": _safe_manager_list(cv, "certifications"),
        "volunteers": _safe_manager_list(cv, "volunteers"),
        "projects": _safe_manager_list(cv, "projects"),
        "hobbies": _safe_manager_list(cv, "hobbies"),
    }
    base.update(extra or {})
    return base


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


# ---------------------------
# Pages & CRUD (inchangés fonctionnellement)
# ---------------------------
def index(request):
    return render(request, "cv_generator/index.html")

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from billing.services import has_active_access, has_session_access

@login_required
def cv_list(request):
    if not has_active_access(request.user) and not has_session_access(request):
        return redirect(f"/billing/pricing/?next={request.path}")

    cvs = CV.objects.filter(utilisateur=request.user).order_by("-date_modification")
    return render(request, "cv_generator/cv_list.html", {"cvs": cvs})


@login_required
def template_selection(request):
    # Les 4 styles que tu veux afficher
    styles = ["canada", "europe", "modern", "professional"]
    templates = (
        CVTemplate.objects
        .filter(is_active=True, style_type__in=styles)
        .order_by("style_type", "name")
    )
    return render(request, "cv_generator/template_selection.html", {"templates": templates})

@login_required
def create_cv(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)

    if request.method == "POST":
        form = Step1Form(request.POST, instance=cv)
        if form.is_valid():
            cv_obj = form.save(commit=False)
            cv_obj.utilisateur = request.user
            cv_obj.step1_completed = True
            cv_obj.current_step = 2
            cv_obj.save()

            # Mettre à jour data.personal_info depuis cleaned_data
            pi = {
                "nom": form.cleaned_data.get("nom", "") or "",
                "prenom": form.cleaned_data.get("prenom", "") or "",
                "email": form.cleaned_data.get("email", "") or "",
                "telephone": form.cleaned_data.get("telephone", "") or "",
            }
            cv_obj.data["personal_info"] = pi
            cv_obj.save(update_fields=["data"])

            messages.success(request, "✅ Étape 1 complétée avec succès !")
            return redirect("cv_generator:create_cv_step2", cv_id=cv_obj.id)
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = Step1Form(instance=cv)

    return render(request, "cv_generator/create_cv.html", _cv_context(cv, 1, form=form))


@login_required
def create_cv_step2(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        company = request.POST.get('company', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip() or None
        location = request.POST.get('location', '').strip()
        description_raw = request.POST.get('description_raw', '').strip()

        if not all([title, company, start_date, description_raw]):
            messages.error(request, '❌ Veuillez remplir tous les champs obligatoires (*)')
            return redirect("cv_generator:create_cv_step2", cv_id=cv.id)

        try:
            Experience.objects.create(
                cv=cv,
                title=title,
                company=company,
                start_date=start_date,
                end_date=end_date if end_date else None,
                location=location,
                description_raw=description_raw
            )

            if not cv.step2_completed:
                cv.step2_completed = True
                cv.current_step = 3
                cv.save(update_fields=["step2_completed", "current_step"])

            messages.success(request, "✅ Expérience ajoutée avec succès !")
            return redirect("cv_generator:create_cv_step2", cv_id=cv.id)

        except Exception as e:
            logger.error("Erreur lors de l'ajout d'expérience: %s", e)
            messages.error(request, f"❌ Erreur lors de l'ajout : {str(e)}")
            return redirect("cv_generator:create_cv_step2", cv_id=cv.id)

    return render(request, "cv_generator/create_cv.html", _cv_context(cv, 2))


@login_required
def create_cv_step3(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)

    context = _cv_context(
        cv, 3,
        education_form=EducationForm(),
        skill_form=SkillForm(),
        language_form=LanguageForm(),
        certification_form=CertificationForm(),
        volunteer_form=VolunteerForm(),
        project_form=ProjectForm(),
        hobby_form=HobbyForm(),
    )

    if cv.current_step != 3:
        cv.current_step = 3
        cv.save(update_fields=["current_step"])

    return render(request, "cv_generator/create_cv.html", context)


@login_required
def delete_experience(request, cv_id, exp_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    exp = get_object_or_404(Experience, id=exp_id, cv=cv)
    exp.delete()
    messages.success(request, "✅ Expérience supprimée.")

    if cv.experiences.count() == 0 and cv.step2_completed:
        cv.step2_completed = False
        cv.current_step = 2
        cv.save(update_fields=["step2_completed", "current_step"])

    return redirect("cv_generator:create_cv_step2", cv_id=cv.id)


@login_required
def add_education(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        form = EducationForm(request.POST)
        if form.is_valid():
            edu = form.save(commit=False)
            edu.cv = cv
            edu.save()
            messages.success(request, "✅ Formation ajoutée avec succès !")
        else:
            messages.error(request, "❌ Erreur lors de l'ajout de la formation.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def delete_education(request, cv_id, edu_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    edu = get_object_or_404(Education, id=edu_id, cv=cv)
    edu.delete()
    messages.success(request, "✅ Formation supprimée.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


# ---------------------------
# Skills: robust creation / suppression
# ---------------------------
def _has_field(model_instance, field_name):
    try:
        return any(f.name == field_name for f in model_instance._meta.fields)
    except Exception:
        return False


@login_required
def add_skill(request, cv_id):
    """
    Ajout de compétence: résilient si Skill a ou non un ForeignKey vers CV.
    Si Skill n'a pas de champ 'cv' mais CV possède une relation M2M .skills, on l'ajoute.
    """
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            # Si le modèle Skill a un champ 'cv', on l'affecte
            if _has_field(skill, "cv"):
                try:
                    setattr(skill, "cv", cv)
                except Exception:
                    pass
            # Save toujours
            skill.save()

            # Si cv possède une relation M2M .skills, on l'ajoute (sécurise les 2 cas)
            cv_skills = getattr(cv, "skills", None)
            try:
                if hasattr(cv_skills, "add"):
                    cv_skills.add(skill)
            except Exception:
                # ignore si pas possible
                pass

            messages.success(request, "✅ Compétence ajoutée avec succès !")
        else:
            messages.error(request, "❌ Erreur lors de l'ajout de la compétence.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def delete_skill(request, cv_id, skill_id):
    """
    Suppression résiliente de compétence:
    - si Skill.cv existe -> on exige ownership
    - sinon si cv.skills M2M existe -> on supprime la relation et éventuellement l'objet
    - sinon on renvoie 403 pour ne pas supprimer une compétence globale
    """
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    skill = get_object_or_404(Skill, id=skill_id)

    # si skill a champ 'cv', vérifier correspondance
    if _has_field(skill, "cv"):
        try:
            if getattr(skill, "cv", None) != cv:
                messages.error(request, "❌ Accès refusé à cette compétence.")
                return redirect("cv_generator:create_cv_step3", cv_id=cv.id)
            skill.delete()
            messages.success(request, "✅ Compétence supprimée.")
            return redirect("cv_generator:create_cv_step3", cv_id=cv.id)
        except Exception:
            messages.error(request, "❌ Erreur lors de la suppression de la compétence.")
            return redirect("cv_generator:create_cv_step3", cv_id=cv.id)

    # sinon, si CV possède relation M2M .skills
    cv_skills = getattr(cv, "skills", None)
    if hasattr(cv_skills, "remove"):
        try:
            if skill in cv_skills.all():
                cv_skills.remove(skill)
                # supprimer l'objet si tu veux ; ici on supprime aussi
                skill.delete()
                messages.success(request, "✅ Compétence supprimée.")
                return redirect("cv_generator:create_cv_step3", cv_id=cv.id)
        except Exception:
            messages.error(request, "❌ Erreur lors de la suppression de la compétence.")
            return redirect("cv_generator:create_cv_step3", cv_id=cv.id)

    # cas par défaut : on refuse pour éviter de supprimer une compétence globale non liée
    messages.error(request, "❌ Impossible de supprimer cette compétence (non liée au CV).")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


# ---------------------------
# Languages CRUD (inchangés)
# ---------------------------
@login_required
def add_language(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        form = LanguageForm(request.POST)
        if form.is_valid():
            lang = form.save(commit=False)
            # si Language a champ cv -> l'affecter
            if _has_field(lang, "cv"):
                try:
                    setattr(lang, "cv", cv)
                except Exception:
                    pass
            lang.save()
            messages.success(request, "✅ Langue ajoutée avec succès !")
        else:
            messages.error(request, "❌ Erreur lors de l'ajout de la langue.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def delete_language(request, cv_id, lang_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    lang = get_object_or_404(Language, id=lang_id, cv=cv)
    lang.delete()
    messages.success(request, "✅ Langue supprimée.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


# ---------------------------
# Certifications / Volunteers / Projects / Hobbies (inchangés)
# ---------------------------
@login_required
def add_certification(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        form = CertificationForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            if _has_field(cert, "cv"):
                try:
                    setattr(cert, "cv", cv)
                except Exception:
                    pass
            cert.save()
            messages.success(request, "✅ Certification ajoutée avec succès !")
        else:
            messages.error(request, "❌ Erreur lors de l'ajout de la certification.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def delete_certification(request, cv_id, cert_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    cert = get_object_or_404(Certification, id=cert_id, cv=cv)
    cert.delete()
    messages.success(request, "✅ Certification supprimée.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def add_volunteer(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        form = VolunteerForm(request.POST)
        if form.is_valid():
            vol = form.save(commit=False)
            if _has_field(vol, "cv"):
                try:
                    setattr(vol, "cv", cv)
                except Exception:
                    pass
            vol.save()
            messages.success(request, "✅ Expérience bénévole ajoutée avec succès !")
        else:
            messages.error(request, "❌ Erreur lors de l'ajout de l'expérience bénévole.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def delete_volunteer(request, cv_id, vol_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    vol = get_object_or_404(Volunteer, id=vol_id, cv=cv)
    vol.delete()
    messages.success(request, "✅ Expérience bénévole supprimée.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def add_project(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            proj = form.save(commit=False)
            if _has_field(proj, "cv"):
                try:
                    setattr(proj, "cv", cv)
                except Exception:
                    pass
            proj.save()
            messages.success(request, "✅ Projet ajouté avec succès !")
        else:
            messages.error(request, "❌ Erreur lors de l'ajout du projet.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def delete_project(request, cv_id, proj_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    proj = get_object_or_404(Project, id=proj_id, cv=cv)
    proj.delete()
    messages.success(request, "✅ Projet supprimé.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def add_hobby(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        form = HobbyForm(request.POST)
        if form.is_valid():
            hobby = form.save(commit=False)
            if _has_field(hobby, "cv"):
                try:
                    setattr(hobby, "cv", cv)
                except Exception:
                    pass
            hobby.save()
            messages.success(request, "✅ Centre d'intérêt ajouté avec succès !")
        else:
            messages.error(request, "❌ Erreur lors de l'ajout du centre d'intérêt.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
def delete_hobby(request, cv_id, hobby_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    hobby = get_object_or_404(Hobby, id=hobby_id, cv=cv)
    hobby.delete()
    messages.success(request, "✅ Centre d'intérêt supprimé.")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


# ---------------------------
# Résumé + finalisation
# ---------------------------
@login_required
def update_summary(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    if request.method == "POST":
        summary = request.POST.get('summary', '').strip()
        cv.summary = summary
        cv.save(update_fields=["summary"])
        messages.success(request, "✅ Résumé professionnel sauvegardé !")
    return redirect("cv_generator:create_cv_step3", cv_id=cv.id)


@login_required
@require_POST
def complete_cv(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    cv.is_completed = True
    cv.step3_completed = True
    if not cv.date_completion:
        cv.date_completion = timezone.now()
    cv.save(update_fields=["is_completed", "step3_completed", "date_completion"])
    return JsonResponse({"success": True, "message": "CV marqué comme terminé"})


# ---------------------------
# Normalisation & helpers pour export PDF
# ---------------------------
def _clean_description_text(text: str) -> str:
    if not text:
        return ""
    s = str(text)
    s = re.sub(r'(?is)<\s*br\s*/?\s*>', '\n', s)
    s = re.sub(r'(?is)</?\s*(p|li|ul|ol|div|span)[^>]*>', '\n', s)
    s = re.sub(r'(?is)<[^>]+>', ' ', s)
    s = s.replace('&bull;', '•')
    lines = []
    for ln in s.splitlines():
        ln = re.sub(r'^\s*(?:[•\-\–\—\*]+)\s*', '', ln.strip())
        if not ln:
            continue
        if not re.search(r'[A-Za-zÀ-ÿ0-9]', ln):
            continue
        lines.append(re.sub(r'\s{2,}', ' ', ln))
    merged = []
    buf = ''
    for ln in lines:
        if len(ln) < 20 and not re.search(r'[.!?:;]$', ln):
            buf = (buf + ' ' + ln).strip()
        else:
            if buf:
                merged.append(buf)
                buf = ''
            merged.append(ln)
    if buf:
        merged.append(buf)
    return "\n".join(merged[:15])


def _bullets_from_text(text: str) -> list:
    clean = _clean_description_text(text)
    return [ln.strip() for ln in clean.split("\n") if ln.strip()]


def _norm(s):
    return (s or "").strip().lower()


def _resolve_pdf_template_for_cv(cv, request=None):
    base = "cv_generator/templates_pdf/"
    mapping = {
        # Modernes (4 que tu gardes)
        "canadian":      base + "cv_canada.html",
        "canada":        base + "cv_canada.html",     # alias accepté
        "european":      base + "cv_europe.html",
        "europe":        base + "cv_europe.html",     # alias accepté
        "modern":        base + "cv_modern.html",
        "professional":  base + "cv_professional.html",

        # Autres styles (laisse mappés si jamais un ancien objet traîne)
        "linkedin":      base + "cv_linkedin.html",
        "faang":         base + "cv_faang.html",
        "ats":           base + "cv_ats_ultra.html",
        "europass":      base + "cv_europe.html",
        "professionnel": base + "cv_professional.html",
        "moderne":       base + "cv_modern.html",
    }

    # 1) Override via ?t=...
    if request:
        t = (request.GET.get("t") or "").strip().lower()
        if t in mapping:
            return mapping[t]

    # 2) Depuis l’objet template
    style = (getattr(cv.template, "style_type", "") or "").strip().lower() if getattr(cv, "template", None) else ""
    name  = (getattr(cv.template, "name", "") or "").strip().lower() if getattr(cv, "template", None) else ""

    if style in mapping:
        return mapping[style]

    for key in mapping.keys():
        if key and key in name:
            return mapping[key]

    # 3) Fallback
    return "cv_generator/cv_template_pdf.html"

# ---------------------------
# EXPORT PDF (remplacé par version robuste)
# ---------------------------

# cv_generator/views.py
@login_required
def export_pdf(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)

    # Historique (best effort)
    try:
        CVExportHistory.objects.create(cv=cv, export_format='pdf')
    except Exception:
        pass

    # ---- Infos perso ----
    try:
        pi = cv.get_personal_info() or {}
    except Exception:
        pi = (getattr(cv, "data", {}) or {}).get("personal_info", {}) or {}

    # Alias legacy exposés sur cv (lecture seule pour le template)
    for key in ("nom", "prenom", "email", "telephone", "titre", "ville", "province", "pays", "linkedin"):
        if not hasattr(cv, key):
            try:
                setattr(cv, key, pi.get(key, ""))
            except Exception:
                pass

    safe_nom = (pi.get("nom") or getattr(cv, "nom", "") or "CV").strip()
    filename = f"CV_{slugify(safe_nom) or 'document'}.pdf"

    # ---- Résumé ----
    try:
        summary_txt = cv.get_summary() or ""
    except Exception:
        summary_txt = getattr(cv, "summary", "") or ""

    # ---- Build helpers sans muter les objets ORM ----
    def exp_to_dict(e):
        title      = getattr(e, "title",      getattr(e, "titre_poste", "")) or ""
        company    = getattr(e, "company",    getattr(e, "entreprise", ""))  or ""
        start_date = getattr(e, "start_date", getattr(e, "date_debut", None))
        end_date   = getattr(e, "end_date",   getattr(e, "date_fin", None))
        location   = getattr(e, "location",   getattr(e, "lieu", "")) or ""
        raw_desc   = (
            getattr(e, "description_optimised", "")
            or getattr(e, "description_raw", "")
            or getattr(e, "description", "")
        )
        description = _clean_description_text(raw_desc)
        bullets     = _bullets_from_text(raw_desc)
        return {
            # champs modernes
            "title": title, "company": company, "start_date": start_date, "end_date": end_date, "location": location,
            "description": description, "bullets": bullets,
            # alias legacy (pour templates qui les lisent)
            "titre_poste": title, "entreprise": company, "date_debut": start_date, "date_fin": end_date, "lieu": location,
        }

    def edu_to_dict(ed):
        degree     = getattr(ed, "degree",     getattr(ed, "diplome",   getattr(ed, "diploma", ""))) or ""
        school     = getattr(ed, "school",     getattr(ed, "ecole",     getattr(ed, "institution", ""))) or ""
        start_date = getattr(ed, "start_date", getattr(ed, "date_debut", None))
        end_date   = getattr(ed, "end_date",   getattr(ed, "date_fin",   None))
        location   = getattr(ed, "location",   getattr(ed, "lieu", "")) or ""
        desc       = getattr(ed, "description", "")
        return {
            "degree": degree, "school": school, "start_date": start_date, "end_date": end_date, "location": location,
            "description": desc,
            # alias legacy
            "diplome": degree, "ecole": school, "date_debut": start_date, "date_fin": end_date, "lieu": location,
        }

    # ---- Collections "safe" (listes de dicts) ----
    experiences = [exp_to_dict(e) for e in getattr(cv, "experiences", []).all()] if hasattr(cv, "experiences") else []
    educations  = [edu_to_dict(ed) for ed in getattr(cv, "education_set", []).all()] if hasattr(cv, "education_set") else []

    # Skills : on passe les objets tels quels (les templates lisent .name/.nom)
    skills = list(getattr(cv, "skills", []).all()) if hasattr(cv, "skills") else []
    if not skills:
        # fallback JSON (si tu stockes parfois dans cv.data)
        raw_skills = cv.get_skills() or []
        tmp = []
        for s in raw_skills:
            if isinstance(s, str):
                tmp.append(type("S", (), {"name": s, "nom": s})())
            elif isinstance(s, dict):
                nm = s.get("name") or s.get("nom") or s.get("label") or ""
                if nm:
                    tmp.append(type("S", (), {"name": nm, "nom": nm})())
        skills = tmp

    languages      = list(getattr(cv, "languages", []).all()) if hasattr(cv, "languages") else []
    certifications = list(getattr(cv, "certifications", []).all()) if hasattr(cv, "certifications") else []
    volunteers     = list(getattr(cv, "volunteers", []).all()) if hasattr(cv, "volunteers") else []
    projects       = list(getattr(cv, "projects", []).all()) if hasattr(cv, "projects") else []
    hobbies        = list(getattr(cv, "hobbies", []).all()) if hasattr(cv, "hobbies") else []

    context = {
        "cv": cv,
        "personal_info": pi,
        "summary": summary_txt,
        "experiences": experiences,
        "educations": educations,
        "skills": skills,
        "languages": languages,
        "certifications": certifications,
        "volunteers": volunteers,
        "projects": projects,
        "hobbies": hobbies,
        "nom": safe_nom,
    }

    # Choix template
    template_path = _resolve_pdf_template_for_cv(cv, request=request)
    logger.info("Template PDF utilisé: %s (cv_id=%s)", template_path, cv.id)

    # Rendu HTML
    try:
        html = render_to_string(template_path, context, request=request)
    except Exception:
        logger.exception("Rendu échoué sur %s, fallback générique", template_path)
        html = render_to_string("cv_generator/cv_template_pdf.html", context)
        template_path = "cv_generator/cv_template_pdf.html"

    # PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Template-Used"] = template_path

    pisa_status = pisa.CreatePDF(src=html, dest=response)
    if getattr(pisa_status, "err", 0):
        logger.error("Erreur xhtml2pdf (%s) sur template %s", pisa_status.err, template_path)
        return HttpResponse("Erreur lors de la génération du PDF", status=500)

    return response


# ---------------------------
# IA / API rest (inchangés)
# ---------------------------
@login_required
@require_POST
def set_template(request):
    data = _json_body(request)
    template_id = data.get("template_id")
    if not template_id:
        return JsonResponse({"success": False, "error": "template_id manquant"}, status=400)

    template = get_object_or_404(CVTemplate, id=template_id, is_active=True)

    cv = CV.objects.create(
        utilisateur=request.user,
        template=template,
        current_step=1,
        step1_completed=False,
        step2_completed=False,
        step3_completed=False,
        is_completed=False,
        is_published=False,
        data={},
    )

    redirect_url = redirect("cv_generator:create_cv", cv_id=cv.id).url
    return JsonResponse({"success": True, "data": {"cv_id": cv.id, "redirect_url": redirect_url}})


@login_required
def recommend_templates(request):
    templates = list(
        CVTemplate.objects
        .filter(is_active=True)
        .values('id', 'name', 'description', 'style_type')
    )
    return JsonResponse({"success": True, "data": templates})


@login_required
@require_POST
def generate_summary(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
    personal = cv.get_personal_info()
    job_title = cv.profession or personal.get("profession") or "Professionnel"
    country = cv.pays_cible or "International"
    industry = cv.template.industry if cv.template else "Général"
    years = 0

    if _ai_service:
        try:
            items = _ai_service.generate_career_summaries(job_title, years, industry, country)
            return JsonResponse({"success": True, "data": items})
        except Exception as e:
            logger.warning("IA generate_summary erreur: %s", e)

    demos = [
        f"{job_title} orienté résultats, apte à livrer dans des environnements {industry}, culture {country}.",
        f"Profil {job_title} avec sens du détail, collaboration et rigueur, prêt pour le marché {country}.",
        f"Expérience en projets {industry}, communication claire et focus qualité, mobile {country}.",
    ]
    return JsonResponse({"success": True, "data": demos})


@login_required
@require_POST
def clarify_experience(request):
    body = _json_body(request)
    raw_description = body.get("description", "") or ""
    job_title = body.get("job_title", "Professionnel")
    industry = body.get("industry", "Général")
    if _ai_service:
        try:
            qs = _ai_service.generate_clarifying_questions(raw_description, job_title, industry)
            return JsonResponse({"success": True, "data": qs})
        except Exception as e:
            logger.warning("IA clarify_experience erreur: %s", e)
    return JsonResponse({"success": True, "data": [
        "Pouvez-vous quantifier vos résultats (chiffres, pourcentages) ?",
        "Quelle était la taille de l'équipe et votre rôle exact ?",
        "Quels outils/technologies avez-vous utilisés ?",
        "Quel impact mesurable pour l'entreprise ?"
    ]})


@login_required
@require_POST
def enhance_experience(request):
    body = _json_body(request)
    raw = body.get("description", "") or ""
    job_title = body.get("job_title", "Professionnel")
    industry = body.get("industry", "Général")
    clar = body.get("clarifications") or {}
    if _ai_service:
        try:
            text = _ai_service.enhance_experience_description(raw, job_title, industry, clarifications=clar)
            return JsonResponse({"success": True, "data": text})
        except Exception as e:
            logger.warning("IA enhance_experience erreur: %s", e)
    return JsonResponse({"success": True, "data": f"✓ {raw.strip()[:160]}"})


@login_required
@require_POST
def optimize_skills(request):
    body = _json_body(request)
    skills = body.get("skills", []) or []
    job_title = body.get("job_title", "Professionnel")
    industry = body.get("industry", "Général")
    country = body.get("country", "International")
    if _ai_service:
        try:
            data = _ai_service.optimize_skills(skills, job_title, industry, country)
            return JsonResponse({"success": True, "data": data})
        except Exception as e:
            logger.warning("IA optimize_skills erreur: %s", e)
    return JsonResponse({"success": True, "data": {
        "categorized": {"technical": skills, "languages": [], "soft": []},
        "suggestions": ["Git", "Docker", "CI/CD"],
        "ats_keywords": ["Agile", "Project Management"]
    }})


@login_required
@require_POST
def analyze_cv(request, cv_id=None):
    if cv_id:
        cv = get_object_or_404(CV, id=cv_id, utilisateur=request.user)
        cv_data = {
            "personal_info": cv.get_personal_info(),
            "profession": cv.profession,
            "pays_cible": cv.pays_cible,
            "summary": cv.get_summary(),
            "experiences": list(cv.experiences.values()) if hasattr(cv, "experiences") else [],
            "skills": list(cv.skills.values()) if hasattr(cv, "skills") else [],
            "languages": list(cv.languages.values()) if hasattr(cv, "languages") else [],
            "education": list(cv.education_set.values()) if hasattr(cv, "education_set") else [],
        }
        industry = cv.template.industry if cv.template else "Général"
        country = cv.pays_cible or "International"
    else:
        body = _json_body(request)
        cv_data = body.get("cv_data", {}) or {}
        industry = body.get("industry", "Général")
        country = body.get("country", "International")

    if _ai_service:
        try:
            res = _ai_service.analyze_cv_quality(cv_data, industry, country)
            return JsonResponse({"success": True, "data": res})
        except Exception as e:
            logger.warning("IA analyze_cv erreur: %s", e)

    return JsonResponse({"success": True, "data": {
        "ats_score": 60,
        "breakdown": {"ats_compatibility": 20, "action_verbs": 12, "quantification": 14, "grammar": 14},
        "recommendations": [
            "Ajoutez plus de métriques chiffrées.",
            "Commencez par des verbes d'action.",
            "Incorporez des mots-clés du poste."
        ]
    }})

