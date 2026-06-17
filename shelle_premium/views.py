import csv

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import PrestataireForm
from .models import Prestataire


@require_http_methods(["GET", "POST"])
def formulaire(request):
    """Affiche le formulaire prestataire et traite la soumission AJAX."""

    if request.method == "POST":
        form = PrestataireForm(request.POST)
        if form.is_valid():
            prestataire = form.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Carte Shelle Premium validee avec succes.",
                    "prestataire": {
                        "nom_complet": prestataire.nom_complet,
                        "code_premium": prestataire.code_premium,
                    },
                }
            )
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return render(request, "shelle_premium/formulaire.html", {"form": PrestataireForm()})


@staff_member_required
def dashboard(request):
    """Tableau de bord staff des prestataires Shelle Premium."""

    prestataires = list(Prestataire.objects.all())
    actifs = sum(1 for item in prestataires if item.est_actif())
    expires = len(prestataires) - actifs
    return render(
        request,
        "shelle_premium/dashboard.html",
        {
            "prestataires": prestataires,
            "total": len(prestataires),
            "actifs": actifs,
            "expires": expires,
        },
    )


@staff_member_required
def export_csv(request):
    """Exporte tous les prestataires Shelle Premium au format CSV."""

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="shelle-premium-prestataires.csv"'
    writer = csv.writer(response)
    writer.writerow(["Nom complet", "Code Premium", "Date Expiration", "Adresse", "Date inscription", "Statut"])
    for prestataire in Prestataire.objects.all():
        writer.writerow(
            [
                prestataire.nom_complet,
                prestataire.code_premium,
                prestataire.date_expiration,
                prestataire.adresse,
                prestataire.date_inscription.strftime("%Y-%m-%d %H:%M"),
                "Actif" if prestataire.est_actif() else "Expire",
            ]
        )
    return response

