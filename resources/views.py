import mimetypes
import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from billing.services import has_candidate_access
from .models import Resource


def library(request):
    qs = Resource.objects.filter(is_active=True)

    # Filtres
    category = request.GET.get("cat", "")
    destination = request.GET.get("dest", "")
    filtre = request.GET.get("filtre", "")  # "free" | "premium"

    if category:
        qs = qs.filter(category=category)
    if destination:
        qs = qs.filter(destination=destination)
    if filtre == "free":
        qs = qs.filter(is_free=True)
    elif filtre == "premium":
        qs = qs.filter(is_premium=True)

    has_premium = request.user.is_authenticated and has_candidate_access(request.user)

    context = {
        "resources": qs,
        "total": Resource.objects.filter(is_active=True).count(),
        "categories": Resource.CATEGORY_CHOICES,
        "destinations": Resource.DESTINATION_CHOICES,
        "selected_cat": category,
        "selected_dest": destination,
        "selected_filtre": filtre,
        "has_premium": has_premium,
    }
    return render(request, "resources/library.html", context)


def download(request, pk):
    resource = get_object_or_404(Resource, pk=pk, is_active=True)

    if not resource.file:
        raise Http404

    # Ressource premium : abonnement candidat requis
    if resource.is_premium:
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            from django.urls import reverse
            return redirect(f"{reverse('authentification:login')}?next={request.path}")
        if not has_candidate_access(request.user):
            from django.shortcuts import redirect
            from django.urls import reverse
            from django.contrib import messages
            messages.error(request, "🔒 Abonnement Premium requis pour télécharger cette ressource.")
            return redirect(f"{reverse('billing:pricing')}?next={request.path}")

    file_path = resource.file.path
    if not os.path.exists(file_path):
        raise Http404

    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or "application/octet-stream"
    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
