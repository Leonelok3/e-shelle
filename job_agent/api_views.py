# job_agent/api_views.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import ApplicationPack, CandidateDocuments, CandidateProfile, JobLead
from .views import build_or_update_pack  # on réutilise ta fonction existante


def _safe_attr(obj, name: str, default: str = "") -> str:
    return getattr(obj, name, default) or default


def _build_cv_url(request, docs: CandidateDocuments) -> str:
    """
    Retourne l'URL absolue du fichier CV si disponible.
    """
    try:
        if getattr(docs, "cv_file", None):
            return request.build_absolute_uri(docs.cv_file.url)
    except Exception:
        pass
    return ""


@require_GET
@login_required
def indeed_autofill(request, lead_id: int):
    """
    ✅ Endpoint "session-based" (cookie Django, login requis)
    Utile pour tester en local ou depuis Immigration97.
    """
    lead = get_object_or_404(JobLead, id=lead_id, user=request.user)
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    docs, _ = CandidateDocuments.objects.get_or_create(user=request.user)

    pack, created = ApplicationPack.objects.get_or_create(user=request.user, lead=lead)
    pack_missing = (
        created
        or not (pack.generated_letter or "").strip()
        or not (pack.generated_email or "").strip()
        or not (pack.email_subject or "").strip()
    )
    if pack_missing:
        pack = build_or_update_pack(user=request.user, lead=lead, profile=profile, docs=docs)

    cv_url = _build_cv_url(request, docs)

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
            "email": _safe_attr(profile, "email") or (request.user.email or ""),
            "phone": _safe_attr(profile, "phone"),
            "city": _safe_attr(profile, "city"),
            "linkedin": _safe_attr(profile, "linkedin_url"),
            "portfolio": _safe_attr(docs, "portfolio_url") or _safe_attr(profile, "portfolio_url"),
            "cv_file_url": cv_url,  # ✅ utile pour l'extension
        },
        "application": {
            "email_subject": pack.email_subject or "",
            "email_body": pack.generated_email or "",
            "cover_letter": pack.generated_letter or "",
            "answers": pack.suggested_answers or {},
        },
    }
    return JsonResponse(data)


@require_GET
def indeed_autofill_token(request, lead_id: int):
    """
    ✅ Endpoint "token-based" (AUCUN cookie requis)
    L'extension appelle:
      /jobs/api/indeed/autofill-token/<lead_id>/?t=<token>

    Token attendu (signing.dumps) :
      {"uid": <user_id>, "lead_id": <lead_id>}
    """
    token = (request.GET.get("t") or "").strip()
    if not token:
        return JsonResponse({"error": "missing_token"}, status=401)

    try:
        payload = signing.loads(token, salt="imm97_autofill", max_age=60 * 60)  # 1h
    except signing.SignatureExpired:
        return JsonResponse({"error": "token_expired"}, status=401)
    except signing.BadSignature:
        return JsonResponse({"error": "invalid_token"}, status=401)
    except Exception:
        return JsonResponse({"error": "invalid_token"}, status=401)

    user_id = payload.get("uid")
    token_lead_id = payload.get("lead_id")

    if not user_id or not token_lead_id:
        return JsonResponse({"error": "bad_token_payload"}, status=401)

    # ✅ sécurité: le token doit correspondre au lead demandé
    try:
        if int(token_lead_id) != int(lead_id):
            return JsonResponse({"error": "token_lead_mismatch"}, status=403)
    except Exception:
        return JsonResponse({"error": "token_lead_mismatch"}, status=403)

    lead = get_object_or_404(JobLead, id=lead_id, user_id=user_id)
    profile, _ = CandidateProfile.objects.get_or_create(user_id=user_id)
    docs, _ = CandidateDocuments.objects.get_or_create(user_id=user_id)

    pack, created = ApplicationPack.objects.get_or_create(user_id=user_id, lead=lead)
    pack_missing = (
        created
        or not (pack.generated_letter or "").strip()
        or not (pack.generated_email or "").strip()
        or not (pack.email_subject or "").strip()
    )
    if pack_missing:
        pack = build_or_update_pack(user=lead.user, lead=lead, profile=profile, docs=docs)

    cv_url = _build_cv_url(request, docs)

    data = {
        "lead": {
            "id": lead.id,
            "title": lead.title or "",
            "company": lead.company or "",
            "location": lead.location or "",
            "url": lead.url or "",
        },
        "candidate": {
            "full_name": profile.full_name or lead.user.get_username(),
            "email": _safe_attr(profile, "email") or (lead.user.email or ""),
            "phone": _safe_attr(profile, "phone"),
            "city": _safe_attr(profile, "city"),
            "linkedin": _safe_attr(profile, "linkedin_url"),
            "portfolio": _safe_attr(docs, "portfolio_url") or _safe_attr(profile, "portfolio_url"),
            "cv_file_url": cv_url,  # ✅ utile pour l'extension
        },
        "application": {
            "email_subject": pack.email_subject or "",
            "email_body": pack.generated_email or "",
            "cover_letter": pack.generated_letter or "",
            "answers": pack.suggested_answers or {},
        },
    }
    return JsonResponse(data)
