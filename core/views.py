from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.conf import settings
from eligibility.models import Session as EligSession
from xhtml2pdf import pisa
from io import BytesIO
import json
import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

def user_is_subscriber(user):
    # TODO: branchement avec ton module billing
    return True  # pour l’instant on autorise

@login_required
def wizard_page(request):
    if not user_is_subscriber(request.user):
        return redirect("/billing/subscribe/")  # adapte à ta route d’abonnement
    return render(request, "wizard/index.html")

@login_required
def wizard_result_page(request, session_id: int):
    if not user_is_subscriber(request.user):
        return redirect("/billing/subscribe/")
    try:
        sess = EligSession.objects.get(id=session_id, user=request.user)
    except EligSession.DoesNotExist:
        return redirect("/wizard/")
    return render(request, "wizard/result.html", {"session_id": session_id, "result": sess.result_json or {}})

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
    # Si vide, tente de le recharger côté API (en dernier recours)
    if not data or not data.get("results"):
        # Optionnel: ici on pourrait recalculer; pour l'instant on affiche un message
        data = {"results": []}

    html = render(request, "wizard/pdf.html", {"data": data}).content.decode("utf-8")
    pdf_io = BytesIO()
    pisa.CreatePDF(html, dest=pdf_io)
    response = HttpResponse(pdf_io.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="plan_immigration_session_{session_id}.pdf"'
    return response


def user_is_subscriber(user):
    return True  # TODO: brancher plus tard au module billing

@login_required
def wizard_steps_page(request):
    if not user_is_subscriber(request.user):
        return redirect("/billing/subscribe/")
    return render(request, "wizard/steps.html")

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard_page(request):
    return render(request, "dashboard/index.html")
