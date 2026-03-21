import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.db.models.functions import TruncMonth

from .models import RecruiterProfile, InterviewInvite, InterviewInviteStatus
from profiles.models import Profile, RecruiterFavorite

_log = logging.getLogger(__name__)


def _get_or_create_recruiter(user):
    profile, _ = RecruiterProfile.objects.get_or_create(user=user)
    return profile


# ─────────────────────────────────────────
# TABLEAU DE BORD RECRUTEUR
# ─────────────────────────────────────────
@login_required
def dashboard(request):
    rec = _get_or_create_recruiter(request.user)

    invites_qs = InterviewInvite.objects.filter(recruiter=request.user)
    stats = {
        "total": invites_qs.count(),
        "sent": invites_qs.filter(status=InterviewInviteStatus.SENT).count(),
        "accepted": invites_qs.filter(status=InterviewInviteStatus.ACCEPTED).count(),
        "declined": invites_qs.filter(status=InterviewInviteStatus.DECLINED).count(),
    }

    recent_invites = (
        invites_qs
        .select_related("candidate_user__profile")
        .order_by("-created_at")[:6]
    )

    favorites = (
        RecruiterFavorite.objects.filter(recruiter=request.user)
        .select_related("profile__user", "profile__category")
        .order_by("-created_at")[:6]
    )

    invited_ids = list(invites_qs.values_list("candidate_user_id", flat=True))
    suggestions = (
        Profile.objects.filter(is_public=True)
        .exclude(user__in=invited_ids)
        .select_related("user", "category")
        .order_by("-created_at")[:4]
    )

    context = {
        "rec": rec,
        "stats": stats,
        "recent_invites": recent_invites,
        "favorites": favorites,
        "suggestions": suggestions,
        "profile_complete": bool(rec.company_name and rec.description and rec.sector),
    }
    return render(request, "recruiters/dashboard.html", context)


# ─────────────────────────────────────────
# ÉDITION PROFIL ENTREPRISE
# ─────────────────────────────────────────
@login_required
def profile_edit(request):
    rec = _get_or_create_recruiter(request.user)

    if request.method == "POST":
        rec.company_name = request.POST.get("company_name", "").strip()
        rec.description = request.POST.get("description", "").strip()
        rec.sector = request.POST.get("sector", "").strip()
        rec.city = request.POST.get("city", "").strip()
        rec.country = request.POST.get("country", "").strip()
        rec.phone = request.POST.get("phone", "").strip()
        rec.website = request.POST.get("website", "").strip()
        rec.linkedin_url = request.POST.get("linkedin_url", "").strip()
        if "logo" in request.FILES:
            rec.logo = request.FILES["logo"]
        rec.save()
        messages.success(request, "Profil entreprise mis à jour.")
        return redirect("recruiters:dashboard")

    return render(request, "recruiters/profile_edit.html", {"rec": rec})


# ─────────────────────────────────────────
# PAGE PUBLIQUE ENTREPRISE
# ─────────────────────────────────────────
def public_profile(request, pk):
    rec = get_object_or_404(RecruiterProfile, pk=pk)
    invite_count = InterviewInvite.objects.filter(recruiter=rec.user).count()
    accepted_count = InterviewInvite.objects.filter(
        recruiter=rec.user, status=InterviewInviteStatus.ACCEPTED
    ).count()
    return render(request, "recruiters/public_profile.html", {
        "rec": rec,
        "invite_count": invite_count,
        "accepted_count": accepted_count,
    })


# ─────────────────────────────────────────
# MES INVITATIONS (vue complète avec filtres)
# ─────────────────────────────────────────
@login_required
def my_invites(request):
    rec = _get_or_create_recruiter(request.user)
    status_filter = request.GET.get("status", "")
    qs = InterviewInvite.objects.filter(recruiter=request.user).select_related("candidate_user__profile")
    if status_filter in ("sent", "accepted", "declined"):
        qs = qs.filter(status=status_filter)
    invites = qs.order_by("-created_at")
    return render(request, "recruiters/my_invites.html", {
        "rec": rec,
        "invites": invites,
        "status_filter": status_filter,
    })


# ─────────────────────────────────────────
# ANALYTICS RECRUTEUR
# ─────────────────────────────────────────
@login_required
def analytics(request):
    rec = _get_or_create_recruiter(request.user)
    invites_qs = InterviewInvite.objects.filter(recruiter=request.user)

    total = invites_qs.count()
    accepted = invites_qs.filter(status="accepted").count()
    declined = invites_qs.filter(status="declined").count()
    pending = invites_qs.filter(status="sent").count()
    rate = round(accepted / total * 100, 1) if total else 0

    # Par mois (6 derniers mois)
    monthly = list(
        invites_qs
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")[:6]
    )
    monthly_labels = [m["month"].strftime("%b %Y") if m["month"] else "" for m in monthly]
    monthly_data = [m["count"] for m in monthly]

    # Par statut (donut)
    by_status = {
        "sent": pending,
        "accepted": accepted,
        "declined": declined,
    }

    return render(request, "recruiters/analytics.html", {
        "rec": rec,
        "total": total,
        "accepted": accepted,
        "declined": declined,
        "pending": pending,
        "rate": rate,
        "monthly_labels": monthly_labels,
        "monthly_data": monthly_data,
        "by_status": by_status,
    })
