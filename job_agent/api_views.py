from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import JobLead, CandidateProfile, CandidateDocuments, ApplicationPack
from .views import build_or_update_pack  # on réutilise ta fonction existante


@require_GET
@login_required
def indeed_autofill(request, lead_id: int):
    """
    Retourne les données nécessaires à l'extension Chrome pour auto-remplir Indeed.
    """
    lead = get_object_or_404(JobLead, id=lead_id, user=request.user)
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    docs, _ = CandidateDocuments.objects.get_or_create(user=request.user)

    pack, _ = ApplicationPack.objects.get_or_create(user=request.user, lead=lead)
    pack_missing = (
        not (pack.generated_letter or "").strip()
        or not (pack.generated_email or "").strip()
        or not (pack.email_subject or "").strip()
    )
    if pack_missing:
        pack = build_or_update_pack(user=request.user, lead=lead, profile=profile, docs=docs)

    # Helpers safe (si tes champs n'existent pas encore)
    def safe_attr(obj, name: str, default: str = ""):
        return getattr(obj, name, default) or default

    data = {
        "lead": {
            "id": lead.id,
            "title": lead.title or "",
            "company": lead.company or "",
            "location": lead.location or "",
            "url": lead.url or "",
        },
        "candidate": {
            "full_name": profile.full_name or request.user.get_username(),
            "email": safe_attr(profile, "email") or (request.user.email or ""),
            "phone": safe_attr(profile, "phone"),
            "city": safe_attr(profile, "city"),
            "linkedin": safe_attr(profile, "linkedin_url"),
            "portfolio": safe_attr(docs, "portfolio_url") or safe_attr(profile, "portfolio_url"),
        },
        "application": {
            "email_subject": pack.email_subject or "",
            "email_body": pack.generated_email or "",
            "cover_letter": pack.generated_letter or "",
            "answers": pack.suggested_answers or {},
        },
    }

    return JsonResponse(data)
