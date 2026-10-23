import io
import mimetypes
from decimal import Decimal, InvalidOperation

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from edu_platform.forms.challenge_forms import ChallengeSubmissionForm, DailyChallengeForm
from edu_platform.models import ChallengeSubmission, DailyChallenge, SubmissionFile


@require_http_methods(["GET", "POST"])
def challenge_public(request, token):
    challenge = get_object_or_404(DailyChallenge, public_token=token, status=DailyChallenge.Status.PUBLISHED)
    form = ChallengeSubmissionForm(request.POST or None, uploads=request.FILES.getlist("files"))
    if request.method == "POST":
        if not challenge.is_open:
            form.add_error(None, "Ce challenge n’accepte plus de copies.")
        elif form.is_valid():
            submission = form.save(commit=False)
            submission.challenge = challenge
            if request.user.is_authenticated:
                submission.student = request.user
            submission.save()
            for uploaded in request.FILES.getlist("files"):
                mime = "application/pdf" if uploaded.name.lower().endswith(".pdf") else mimetypes.guess_type(uploaded.name)[0]
                item = SubmissionFile.objects.create(
                    submission=submission, file=uploaded,
                    original_name=uploaded.name[:180], mime_type=mime or "application/octet-stream",
                    size_bytes=uploaded.size,
                )
            try:
                from edu_platform.tasks import grade_challenge_submission
                grade_challenge_submission.delay(submission.pk)
            except Exception:
                submission.status = ChallengeSubmission.Status.FAILED
                submission.error_message = "La copie est reçue. La mise en file de correction a échoué; l’équipe peut la relancer."
                submission.save(update_fields=["status", "error_message"])
            return redirect("edu:challenge_result", token=submission.access_token)
    return render(request, "edu_platform/challenges/challenge_public.html", {
        "challenge": challenge, "form": form,
        "leaderboard_url": reverse("edu:challenge_leaderboard", args=[challenge.public_token]),
    })


@require_GET
def challenge_exercise_file(request, token):
    challenge = get_object_or_404(DailyChallenge, public_token=token, status=DailyChallenge.Status.PUBLISHED)
    if not challenge.exercise_file:
        raise Http404
    challenge.exercise_file.open("rb")
    mime = mimetypes.guess_type(challenge.exercise_file.name)[0] or "application/octet-stream"
    return FileResponse(challenge.exercise_file, content_type=mime, filename=challenge.exercise_file.name.rsplit("/", 1)[-1])


@require_GET
def challenge_qr(request, token):
    challenge = get_object_or_404(DailyChallenge, public_token=token, status=DailyChallenge.Status.PUBLISHED)
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
        image = qrcode.make(request.build_absolute_uri(reverse("edu:challenge_public", args=[challenge.public_token])), error_correction=ERROR_CORRECT_M, box_size=8, border=3)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return HttpResponse(output.getvalue(), content_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
    except Exception as exc:
        raise Http404("QR code indisponible") from exc


@require_GET
def challenge_result(request, token):
    submission = get_object_or_404(ChallengeSubmission.objects.select_related("challenge"), access_token=token)
    return render(request, "edu_platform/challenges/submission_result.html", {"submission": submission})


@require_GET
def challenge_leaderboard(request, token):
    challenge = get_object_or_404(DailyChallenge, public_token=token, status=DailyChallenge.Status.PUBLISHED, leaderboard_enabled=True)
    rows = list(challenge.submissions.filter(status__in=[ChallengeSubmission.Status.GRADED, ChallengeSubmission.Status.REVIEWED]).order_by("-score", "submitted_at")[:50])
    return render(request, "edu_platform/challenges/leaderboard.html", {"challenge": challenge, "rows": rows})


@staff_member_required(login_url="/edu/login/")
@require_http_methods(["GET", "POST"])
def challenge_manager(request):
    from django.contrib import messages
    from django.utils import timezone
    from django.db.models import Count

    if request.method == "POST":
        form = DailyChallengeForm(request.POST, request.FILES)
        if form.is_valid():
            challenge = form.save(commit=False)
            challenge.created_by = request.user
            challenge.save()
            messages.success(request, "Challenge enregistré. Le QR code et le lien élève sont prêts.")
            return redirect("edu:challenge_manager")
    else:
        form = DailyChallengeForm()
    challenges = DailyChallenge.objects.annotate(submission_count=Count("submissions")).order_by("-created_at")[:50]
    return render(request, "edu_platform/challenges/manage.html", {"form": form, "challenges": challenges})


@staff_member_required(login_url="/edu/login/")
@require_http_methods(["GET", "POST"])
def challenge_submissions(request, challenge_id):
    from django.contrib import messages
    from django.utils import timezone
    challenge = get_object_or_404(DailyChallenge, pk=challenge_id)
    if request.method == "POST":
        submission = get_object_or_404(ChallengeSubmission, pk=request.POST.get("submission_id"), challenge=challenge)
        if request.POST.get("action") == "retry":
            submission.status = ChallengeSubmission.Status.FAILED
            submission.save(update_fields=["status"])
            try:
                from edu_platform.tasks import grade_challenge_submission
                grade_challenge_submission.delay(submission.pk)
                messages.success(request, "La copie a été remise en file pour correction.")
            except Exception:
                messages.error(request, "La tâche n’a pas pu être mise en file. Vérifie que Celery et son broker sont actifs.")
            return redirect("edu:challenge_submissions", challenge_id=challenge.pk)
        try:
            score = Decimal(request.POST.get("score", ""))
            if score < 0 or score > challenge.total_points:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            messages.error(request, f"La note doit être comprise entre 0 et {challenge.total_points}.")
            return redirect("edu:challenge_submissions", challenge_id=challenge.pk)
        feedback = dict(submission.feedback or {})
        feedback["overall_feedback"] = request.POST.get("overall_feedback", "")[:5000]
        feedback["provisional"] = False
        submission.score = score
        submission.feedback = feedback
        submission.status = ChallengeSubmission.Status.REVIEWED
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.error_message = ""
        submission.save(update_fields=["score", "feedback", "status", "reviewed_by", "reviewed_at", "error_message"])
        messages.success(request, f"Copie de {submission.student_name} vérifiée.")
        return redirect("edu:challenge_submissions", challenge_id=challenge.pk)
    submissions = challenge.submissions.prefetch_related("files").select_related("reviewed_by").order_by("-submitted_at")[:200]
    return render(request, "edu_platform/challenges/submissions.html", {"challenge": challenge, "submissions": submissions})


@staff_member_required
@require_GET
def submission_file(request, submission_id, file_id):
    item = get_object_or_404(SubmissionFile.objects.select_related("submission"), pk=file_id, submission_id=submission_id)
    item.file.open("rb")
    return FileResponse(item.file, content_type=item.mime_type, filename=item.original_name or "copie-eleve", as_attachment=True)
