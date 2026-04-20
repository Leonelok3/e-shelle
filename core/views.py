from datetime import timedelta
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.utils import timezone
from xhtml2pdf import pisa

from actualite.models import NewsItem
from eligibility.models import Session as EligSession
from billing.services import has_active_access

from .models import ConsultationRequest
from .forms import ConsultationForm


def user_is_subscriber(user):
    return has_active_access(user)


@login_required
def wizard_page(request):
    if not user_is_subscriber(request.user):
        return redirect("/billing/subscribe/")
    return render(request, "wizard/index.html")


@login_required
def wizard_steps_page(request):
    if not user_is_subscriber(request.user):
        return redirect("/billing/subscribe/")
    return render(request, "wizard/steps.html")


@login_required
def wizard_result_page(request, session_id: int):
    if not user_is_subscriber(request.user):
        return redirect("/billing/subscribe/")

    try:
        sess = EligSession.objects.get(id=session_id, user=request.user)
    except EligSession.DoesNotExist:
        return redirect("/wizard/")

    return render(
        request,
        "wizard/result.html",
        {
            "session_id": session_id,
            "result": sess.result_json or {},
        },
    )


@login_required
def wizard_pdf(request):
    if not user_is_subscriber(request.user):
        return redirect("/billing/subscribe/")

    session_id = request.GET.get("session_id")
    if not session_id:
        return HttpResponseBadRequest("session_id manquant")

    try:
        sess = EligSession.objects.get(id=int(session_id), user=request.user)
    except EligSession.DoesNotExist:
        return HttpResponseBadRequest("session introuvable")

    data = sess.result_json or {}
    if not data or not data.get("results"):
        data = {"results": []}

    html = render(request, "wizard/pdf.html", {"data": data}).content.decode("utf-8")
    pdf_io = BytesIO()
    pisa.CreatePDF(html, dest=pdf_io)

    response = HttpResponse(pdf_io.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="plan_immigration_session_{session_id}.pdf"'
    return response


@login_required
def dashboard_page(request):
    return render(request, "dashboard/index.html")


def home(request):
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    top_week = (
        NewsItem.objects
        .filter(is_published=True, publish_date__gte=week_ago, publish_date__lte=now)
        .order_by("-views_count", "-publish_date")[:6]
    )

    if not top_week.exists():
        top_week = (
            NewsItem.objects
            .filter(is_published=True)
            .order_by("-is_featured", "-views_count", "-publish_date")[:6]
        )

    return render(request, "home.html", {"top_week": top_week})


# ======================================================
# CONSULTATION / ACCOMPAGNEMENT
# ======================================================

def consultation_request(request):
    """Page publique : demande de consultation / accompagnement personnalisé."""
    if request.method == "POST":
        form = ConsultationForm(request.POST, user=request.user if request.user.is_authenticated else None)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.user = request.user
            obj.save()
            return redirect("consultation_success")
    else:
        form = ConsultationForm(user=request.user if request.user.is_authenticated else None)

    return render(request, "consultation/request.html", {"form": form})


def consultation_success(request):
    """Page de confirmation après soumission d'une demande."""
    return render(request, "consultation/success.html")
