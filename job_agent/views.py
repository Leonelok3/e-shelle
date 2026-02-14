# job_agent/views.py
from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse  # ✅ AJOUT (safe)
from django.utils import timezone

from .forms import (
    CandidateDocumentsForm,
    CandidateProfileForm,
    JobLeadAddForm,
    JobLeadBulkAddForm,
    JobSearchForm,
)
from .models import (
    AnswerTemplate,
    ApplicationPack,
    CandidateDocuments,
    CandidateProfile,
    FollowUpTemplate,
    JobLead,
    JobSearch,
    LetterTemplate,
    PublicJobOffer,
)
from .services import (
    generate_application_texts,
    heuristic_match,
    render_text_template,
    send_followup_email,
)


# ======================================================
# Helpers (internal)
# ======================================================
def _latest_search(user):
    return JobSearch.objects.filter(user=user).order_by("-created_at").first()


def _safe_get_line(block: str, prefix: str) -> str:
    """
    Cherche une ligne qui commence par 'prefix:' (case-insensitive) et retourne la valeur.
    Exemple: prefix='URL' récupère 'URL: https://...'
    """
    if not block:
        return ""
    for line in block.splitlines():
        line = line.strip()
        if line.lower().startswith(prefix.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_description(block: str) -> str:
    """
    Récupère tout ce qui suit 'Description:' dans un bloc.
    """
    if not block:
        return ""
    low = block.lower()
    if "description:" not in low:
        return ""
    idx = low.index("description:")
    return block[idx + len("description:") :].strip()


def _render_letter_from_template(
    template_text: str, *, title: str, company: str, location: str, name: str
) -> str:
    """
    Remplit {title} {company} {location} {name} si présents.
    Si un placeholder est invalide, renvoie le texte brut.
    """
    data = {
        "title": title or "",
        "company": company or "",
        "location": location or "",
        "name": name or "",
    }
    try:
        return (template_text or "").format(**data).strip()
    except Exception:
        return (template_text or "").strip()


def _answers_from_admin_templates(language: str) -> dict:
    """
    Récupère AnswerTemplate actifs pour la langue demandée.
    Retour: { key: content }
    """
    lang = (language or "fr").lower()
    qs = AnswerTemplate.objects.filter(is_active=True, language=lang).order_by("key", "id")
    out: dict[str, str] = {}
    for t in qs:
        out.setdefault(t.key, t.content)
    return out


def _letter_template_for_language(language: str):
    lang = (language or "fr").lower()
    return LetterTemplate.objects.filter(is_active=True, language=lang).order_by("-id").first()


def _followup_template_for_language(language: str):
    lang = (language or "fr").lower()
    return FollowUpTemplate.objects.filter(is_active=True, language=lang).order_by("-id").first()


def _menu_pack_lead_id_for_user(user) -> int | None:
    """
    ✅ Safe helper: permet au menu de générer un lien pack (qui exige lead_id)
    sans casser si l'utilisateur n'a aucune offre.
    """
    lead = JobLead.objects.filter(user=user).order_by("-updated_at", "-created_at").only("id").first()
    return lead.id if lead else None


# ======================================================
# Pages principales
# ======================================================
@login_required
def dashboard(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    docs, _ = CandidateDocuments.objects.get_or_create(user=request.user)

    searches = JobSearch.objects.filter(user=request.user).order_by("-created_at")[:10]
    leads = JobLead.objects.filter(user=request.user).order_by("-created_at")[:20]

    counts = {
        "found": JobLead.objects.filter(user=request.user, status=JobLead.STATUS_FOUND).count(),
        "to_apply": JobLead.objects.filter(user=request.user, status=JobLead.STATUS_TO_APPLY).count(),
        "applied": JobLead.objects.filter(user=request.user, status=JobLead.STATUS_APPLIED).count(),
        "followup": JobLead.objects.filter(user=request.user, status=JobLead.STATUS_FOLLOWUP).count(),
        "reply": JobLead.objects.filter(user=request.user, status=JobLead.STATUS_REPLY).count(),
    }

    # ✅ AJOUTS SAFE POUR LE FRONT (ne casse rien)
    menu_pack_lead_id = _menu_pack_lead_id_for_user(request.user)

    return render(
        request,
        "job_agent/dashboard.html",
        {
            "profile": profile,
            "docs": docs,
            "searches": searches,
            "leads": leads,
            "counts": counts,
            # ✅
            "menu_pack_lead_id": menu_pack_lead_id,
            "dashboard_url": reverse("job_agent:dashboard"),
            "leads_url": reverse("job_agent:lead_list"),
            "kanban_url": reverse("job_agent:kanban"),
            "lead_add_url": reverse("job_agent:lead_add"),
        },
    )


@login_required
def profile_edit(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = CandidateProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil candidat mis à jour.")
            return redirect("job_agent:dashboard")
    else:
        form = CandidateProfileForm(instance=profile)

    # ✅ menu safe
    return render(
        request,
        "job_agent/profile_form.html",
        {
            "form": form,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
        },
    )


@login_required
def documents_edit(request):
    docs, _ = CandidateDocuments.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = CandidateDocumentsForm(request.POST, request.FILES, instance=docs)
        if form.is_valid():
            obj = form.save(commit=False)

            # ✅ Extraction automatique du texte du CV PDF
            auto_extract = form.cleaned_data.get("auto_extract_cv", True)
            uploaded_cv = request.FILES.get("cv_file")

            if auto_extract and uploaded_cv:
                from .services import extract_cv_text_from_file

                extracted = extract_cv_text_from_file(uploaded_cv, filename=uploaded_cv.name)

                if extracted.strip():
                    obj.cv_text = extracted
                    messages.success(request, "Texte CV extrait automatiquement depuis le PDF.")
                else:
                    messages.warning(
                        request,
                        "Impossible d’extraire le texte du PDF (scan image ou PDF protégé). "
                        "Dans ce cas, colle le texte du CV manuellement."
                    )

            obj.save()
            messages.success(request, "Documents mis à jour.")
            return redirect("job_agent:dashboard")
    else:
        form = CandidateDocumentsForm(instance=docs)

    # ✅ menu safe
    return render(
        request,
        "job_agent/documents_form.html",
        {
            "form": form,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
        },
    )


@login_required
def search_create(request):
    if request.method == "POST":
        form = JobSearchForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Recherche créée.")
            return redirect("job_agent:lead_list")
    else:
        form = JobSearchForm()

    # ✅ menu safe
    return render(
        request,
        "job_agent/search_form.html",
        {
            "form": form,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
        },
    )


# ======================================================
# Offres (leads)
# ======================================================
@login_required
def lead_list(request):
    leads = JobLead.objects.filter(user=request.user).order_by("-created_at")
    searches = JobSearch.objects.filter(user=request.user).order_by("-created_at")

    # ✅ menu safe
    return render(
        request,
        "job_agent/lead_list.html",
        {
            "leads": leads,
            "searches": searches,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
            "dashboard_url": reverse("job_agent:dashboard"),
            "all_leads_url": reverse("job_agent:lead_list"),
        },
    )


@login_required
def lead_add(request):
    if request.method == "POST":
        form = JobLeadAddForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.user = request.user

            # Si l'utilisateur ne choisit pas de recherche, on met la dernière
            if not lead.search:
                lead.search = _latest_search(request.user)

            try:
                lead.save()
            except IntegrityError:
                messages.warning(request, "Tu as déjà ajouté cette offre (même URL).")
                return redirect("job_agent:lead_list")

            # ✅ AUTO-SCORE DIRECT (gain de temps)
            docs, _ = CandidateDocuments.objects.get_or_create(user=request.user)

            if (lead.description_text or "").strip():
                keywords = lead.search.keywords if lead.search else ""
                try:
                    # IA sémantique si dispo (optionnel)
                    from .ai_matching import semantic_match  # type: ignore

                    score = int(semantic_match(docs.cv_text or "", lead.description_text or ""))
                    lead.match_score = max(0, min(score, 100))
                    lead.match_summary = "Scoring sémantique IA (embeddings)."
                except Exception:
                    res = heuristic_match(docs.cv_text or "", lead.description_text or "", keywords=keywords)
                    lead.match_score = res.score
                    lead.match_summary = res.summary

                if lead.match_score >= 60 and lead.status == JobLead.STATUS_FOUND:
                    lead.status = JobLead.STATUS_TO_APPLY

                lead.save(update_fields=["match_score", "match_summary", "status"])
                messages.success(request, f"Offre ajoutée + scorée automatiquement : {lead.match_score}/100")
            else:
                messages.success(
                    request,
                    "Offre ajoutée. Colle la description de l’offre pour obtenir un scoring automatique.",
                )

            return redirect("job_agent:lead_detail", lead_id=lead.id)
    else:
        form = JobLeadAddForm()
        last_search = _latest_search(request.user)
        if last_search:
            form.initial["search"] = last_search.id

    return render(
        request,
        "job_agent/lead_add.html",
        {
            "form": form,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
        },
    )


@login_required
@transaction.atomic
def lead_detail(request, lead_id: int):
    lead = get_object_or_404(JobLead, id=lead_id, user=request.user)
    docs, _ = CandidateDocuments.objects.get_or_create(user=request.user)
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)

    def compute_score() -> tuple[int, str]:
        cv_text = (docs.cv_text or "").strip()
        offer_text = (lead.description_text or "").strip()
        keywords = lead.search.keywords if lead.search else ""

        if not offer_text:
            return 0, "Aucune description d'offre. Colle la description pour un scoring précis."

        # 1) IA sémantique si dispo
        try:
            from .ai_matching import semantic_match  # type: ignore

            score = semantic_match(cv_text, offer_text)
            return int(score), "Scoring sémantique IA (embeddings)."
        except Exception:
            # 2) fallback heuristique
            res = heuristic_match(cv_text, offer_text, keywords=keywords)
            return res.score, res.summary

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # ======================================================
        # ✅ 1) SAVE CONTACT EMAIL (SAFE)
        # ======================================================
        if action == "save_contact_email":
            email = (request.POST.get("contact_email") or "").strip()

            if not email:
                messages.error(request, "Ajoute un email recruteur.")
                return redirect("job_agent:lead_detail", lead_id=lead.id)

            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Email invalide.")
                return redirect("job_agent:lead_detail", lead_id=lead.id)

            lead.contact_email = email
            lead.save(update_fields=["contact_email"])
            messages.success(request, "Email recruteur enregistré ✅")
            return redirect("job_agent:lead_detail", lead_id=lead.id)

        # ======================================================
        # ✅ 2) SEND FOLLOWUP NOW (SAFE + ANTI-SPAM + TEMPLATE CHECK)
        # ======================================================
        if action == "send_followup_now":
            email = (request.POST.get("contact_email") or lead.contact_email or "").strip()

            if not email:
                messages.error(request, "Ajoute d’abord l’email recruteur.")
                return redirect("job_agent:lead_detail", lead_id=lead.id)

            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Email invalide.")
                return redirect("job_agent:lead_detail", lead_id=lead.id)

            # Anti-spam : 24h minimum entre 2 relances
            if lead.followup_sent_at and (timezone.now() - lead.followup_sent_at) < timedelta(hours=24):
                messages.warning(request, "Relance déjà envoyée récemment. Attends 24h.")
                return redirect("job_agent:lead_detail", lead_id=lead.id)

            language = (lead.search.language if lead.search else (profile.language or "fr")).lower()
            tpl = _followup_template_for_language(language)

            name = profile.full_name or request.user.get_username()
            title = lead.title or (lead.search.title if lead.search else "Poste")
            company = lead.company or ""
            location = lead.location or ""

            if tpl:
                subject = render_text_template(
                    tpl.subject, name=name, title=title, company=company, location=location
                )
                body = render_text_template(
                    tpl.content, name=name, title=title, company=company, location=location
                )
            else:
                subject = f"Relance — {title} ({company})"
                body = (
                    "Bonjour,\n\n"
                    f"Je me permets de relancer ma candidature au poste {title}"
                    f"{(' à ' + location) if location else ''}.\n"
                    "Je reste disponible pour un échange (entretien / test).\n\n"
                    f"Cordialement,\n{name}\n"
                )

            # Sécurité: empêcher sujet/corps vide
            subject = (subject or "").strip()
            body = (body or "").strip()
            if not subject or not body:
                messages.error(
                    request,
                    "Template de relance invalide (objet/corps vide). Corrige dans l’admin.",
                )
                return redirect("job_agent:lead_detail", lead_id=lead.id)

            # Envoi SMTP
            try:
                send_followup_email(to_email=email, subject=subject, body=body)
            except Exception as e:
                messages.error(request, f"Erreur SMTP : {e}")
                return redirect("job_agent:lead_detail", lead_id=lead.id)

            # Update lead
            lead.contact_email = email
            lead.followup_sent_at = timezone.now()
            lead.status = JobLead.STATUS_FOLLOWUP
            lead.save(update_fields=["contact_email", "followup_sent_at", "status"])

            messages.success(request, "Relance envoyée ✅")
            return redirect("job_agent:lead_detail", lead_id=lead.id)

        # ======================================================
        # ✅ 3) SCORE
        # ======================================================
        if action == "score":
            score, summary = compute_score()
            lead.match_score = score
            lead.match_summary = summary

            if lead.match_score >= 60 and lead.status == JobLead.STATUS_FOUND:
                lead.status = JobLead.STATUS_TO_APPLY

            lead.save(update_fields=["match_score", "match_summary", "status"])
            messages.success(request, f"Score mis à jour : {lead.match_score}/100")
            return redirect("job_agent:lead_detail", lead_id=lead.id)

        # ======================================================
        # ✅ 4) GENERATE PACK (EMAIL + LETTRE + REPONSES)
        # ======================================================
        if action == "generate_pack":
            language = (lead.search.language if lead.search else (profile.language or "fr")) or "fr"
            language = (language or "fr").lower()

            admin_answers = _answers_from_admin_templates(language)
            lt = _letter_template_for_language(language)

            offer_title = lead.title or (lead.search.title if lead.search else "Poste")
            company = lead.company or ""
            location = lead.location or ""
            name = profile.full_name or request.user.get_username()

            email_subject = ""
            email_body = ""

            if lt and lt.content:
                letter = _render_letter_from_template(
                    lt.content,
                    title=offer_title,
                    company=company,
                    location=location,
                    name=name,
                )
                answers = admin_answers or {}

                # email via service (même si lettre vient de template)
                data = generate_application_texts(
                    offer_title=offer_title,
                    company=company,
                    location=location,
                    offer_text=lead.description_text or "",
                    cv_text=docs.cv_text or "",
                    base_letter=docs.base_letter_text or "",
                    language=language,
                )
                email_subject = (data.get("email_subject") or "").strip()
                email_body = (data.get("email_body") or "").strip()
            else:
                data = generate_application_texts(
                    offer_title=offer_title,
                    company=company,
                    location=location,
                    offer_text=lead.description_text or "",
                    cv_text=docs.cv_text or "",
                    base_letter=docs.base_letter_text or "",
                    language=language,
                )
                letter = (data.get("letter") or "").strip()
                answers = data.get("answers") or {}
                email_subject = (data.get("email_subject") or "").strip()
                email_body = (data.get("email_body") or "").strip()

                # admin answers priorité
                if admin_answers:
                    merged = dict(answers)
                    for k, v in admin_answers.items():
                        merged[k] = v
                    answers = merged

            pack, _ = ApplicationPack.objects.get_or_create(user=request.user, lead=lead)
            pack.generated_letter = (letter or "").strip()
            pack.suggested_answers = answers or {}
            # Phase 5 champs email
            pack.email_subject = email_subject
            pack.generated_email = email_body
            pack.save()

            messages.success(request, "Pack candidature généré (email + lettre + réponses) ✅")
            return redirect("job_agent:pack_detail", lead_id=lead.id)

        # ======================================================
        # ✅ 5) SET STATUS (auto applied_at)
        # ======================================================
        if action == "set_status":
            new_status = request.POST.get("status")
            valid = {c[0] for c in JobLead.STATUS_CHOICES}

            if new_status in valid:
                lead.status = new_status

                # Auto: date candidature si "Postulée"
                if new_status == JobLead.STATUS_APPLIED and not lead.applied_at:
                    lead.applied_at = timezone.now()

                lead.save(update_fields=["status", "applied_at"])
                messages.success(request, "Statut mis à jour ✅")
            else:
                messages.error(request, "Statut invalide.")

            return redirect("job_agent:lead_detail", lead_id=lead.id)

    # ✅ IMPORTANT: on renvoie aussi profile + status_choices + menu_pack_lead_id
    return render(
        request,
        "job_agent/lead_detail.html",
        {
            "lead": lead,
            "docs": docs,
            "profile": profile,
            "status_choices": JobLead.STATUS_CHOICES,
            "menu_pack_lead_id": lead.id,
        },
    )


@login_required
def pack_detail(request, lead_id: int):
    lead = get_object_or_404(JobLead, id=lead_id, user=request.user)
    pack = get_object_or_404(ApplicationPack, lead=lead, user=request.user)

    return render(
        request,
        "job_agent/pack_detail.html",
        {
            "lead": lead,
            "pack": pack,
            "menu_pack_lead_id": lead.id,
            "leads_url": reverse("job_agent:lead_list"),
            "lead_detail_url": reverse("job_agent:lead_detail", kwargs={"lead_id": lead.id}),
        },
    )


# ======================================================
# Offres publiques (admin -> users)
# ======================================================
@login_required
def public_offers(request):
    offers = PublicJobOffer.objects.filter(is_active=True).order_by("-created_at")
    return render(
        request,
        "job_agent/public_offers.html",
        {
            "offers": offers,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
        },
    )


@login_required
@transaction.atomic
def import_public_offer(request, offer_id: int):
    offer = get_object_or_404(PublicJobOffer, id=offer_id, is_active=True)

    try:
        lead = JobLead.objects.create(
            user=request.user,
            search=_latest_search(request.user),
            url=offer.url,
            source=offer.source,
            title=offer.title,
            company=offer.company,
            location=offer.location,
            description_text=offer.description_text,
            status=JobLead.STATUS_FOUND,
        )
    except IntegrityError:
        messages.info(request, "Tu as déjà importé cette offre.")
        return redirect("job_agent:lead_list")

    messages.success(request, "Offre importée dans ton espace.")
    return redirect("job_agent:lead_detail", lead_id=lead.id)


# ======================================================
# Ajout en masse (ultra rapide)
# ======================================================
@login_required
@transaction.atomic
def lead_bulk_add(request):
    """
    L'utilisateur colle plusieurs offres.
    - Par défaut: blocs séparés par '---'
    - Si pas de '---': accepte plusieurs URL (une par ligne) comme import rapide
    """
    if request.method == "POST":
        form = JobLeadBulkAddForm(request.POST)
        if form.is_valid():
            raw = (form.cleaned_data.get("payload") or "").strip()
            default_source = (form.cleaned_data.get("default_source") or "").strip()

            if not raw:
                messages.error(request, "Colle au moins une offre.")
                return redirect("job_agent:lead_bulk_add")

            if "---" in raw:
                blocks = [b.strip() for b in raw.split("---") if b.strip()]
            else:
                # mode simple: une URL par ligne
                urls = [l.strip() for l in raw.splitlines() if l.strip()]
                blocks = [f"URL: {u}" for u in urls]

            last_search = _latest_search(request.user)
            docs, _ = CandidateDocuments.objects.get_or_create(user=request.user)

            created = 0
            skipped = 0

            for b in blocks:
                url = _safe_get_line(b, "url")
                if not url:
                    skipped += 1
                    continue

                title = _safe_get_line(b, "titre")
                company = _safe_get_line(b, "entreprise")
                location = _safe_get_line(b, "lieu")
                source = _safe_get_line(b, "source") or default_source
                desc = _extract_description(b)

                try:
                    lead = JobLead.objects.create(
                        user=request.user,
                        search=last_search,
                        url=url,
                        source=source,
                        title=title,
                        company=company,
                        location=location,
                        description_text=desc,
                        status=JobLead.STATUS_FOUND,
                    )
                except IntegrityError:
                    skipped += 1
                    continue

                # scoring auto si description + CV texte
                if (lead.description_text or "").strip():
                    keywords = last_search.keywords if last_search else ""
                    res = heuristic_match(docs.cv_text or "", lead.description_text or "", keywords=keywords)
                    lead.match_score = res.score
                    lead.match_summary = res.summary
                    if lead.match_score >= 60:
                        lead.status = JobLead.STATUS_TO_APPLY
                    lead.save(update_fields=["match_score", "match_summary", "status"])

                created += 1

            if created:
                messages.success(request, f"{created} offres importées.")
            if skipped:
                messages.info(request, f"{skipped} offres ignorées (URL manquante ou doublons).")

            return redirect("job_agent:lead_list")
    else:
        form = JobLeadBulkAddForm()

    return render(
        request,
        "job_agent/lead_bulk_add.html",
        {
            "form": form,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
        },
    )


# ======================================================
# Kanban (suivi rapide)
# ======================================================
@login_required
def kanban(request):
    leads = JobLead.objects.filter(user=request.user).order_by("-updated_at", "-created_at")

    grouped = {
        JobLead.STATUS_FOUND: [],
        JobLead.STATUS_TO_APPLY: [],
        JobLead.STATUS_APPLIED: [],
        JobLead.STATUS_FOLLOWUP: [],
        JobLead.STATUS_REPLY: [],
    }
    for l in leads:
        grouped.setdefault(l.status, []).append(l)

    return render(
        request,
        "job_agent/kanban.html",
        {
            "grouped": grouped,
            "menu_pack_lead_id": _menu_pack_lead_id_for_user(request.user),
            "leads_url": reverse("job_agent:lead_list"),
            "dashboard_url": reverse("job_agent:dashboard"),
        },
    )


@login_required
@transaction.atomic
def kanban_move(request, lead_id: int):
    lead = get_object_or_404(JobLead, id=lead_id, user=request.user)

    if request.method == "POST":
        new_status = (request.POST.get("status") or "").strip()
        valid = {c[0] for c in JobLead.STATUS_CHOICES}
        if new_status in valid:
            lead.status = new_status

            # ✅ si déplacé en "Postulée" => date candidature
            if new_status == JobLead.STATUS_APPLIED and not lead.applied_at:
                lead.applied_at = timezone.now()

            lead.save(update_fields=["status", "applied_at"])
        else:
            messages.error(request, "Statut invalide.")

    return redirect("job_agent:kanban")
