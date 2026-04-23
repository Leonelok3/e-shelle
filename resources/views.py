import mimetypes
import os

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from billing.services import has_candidate_access
from .models import Resource, ResourcePurchase

WHATSAPP_NUMBER = "237693649944"


def _user_has_access(user, resource):
    """Vérifie si l'utilisateur peut télécharger la ressource."""
    if resource.is_free:
        return True
    if not user.is_authenticated:
        return False
    if has_candidate_access(user):
        return True
    if resource.is_paid():
        return ResourcePurchase.objects.filter(user=user, resource=resource, is_active=True).exists()
    return False


def library(request):
    qs = Resource.objects.filter(is_active=True)

    category = request.GET.get("cat", "")
    destination = request.GET.get("dest", "")
    filtre = request.GET.get("filtre", "")

    if category:
        qs = qs.filter(category=category)
    if destination:
        qs = qs.filter(destination=destination)
    if filtre == "free":
        qs = qs.filter(is_free=True)
    elif filtre == "premium":
        qs = qs.filter(is_premium=True)
    elif filtre == "paid":
        qs = qs.filter(is_free=False, price_xaf__gt=0)

    has_premium = request.user.is_authenticated and has_candidate_access(request.user)

    purchased_ids = set()
    if request.user.is_authenticated:
        purchased_ids = set(
            ResourcePurchase.objects.filter(user=request.user, is_active=True)
            .values_list("resource_id", flat=True)
        )

    featured = Resource.objects.filter(is_active=True, is_featured=True).first()

    context = {
        "resources": qs,
        "total": Resource.objects.filter(is_active=True).count(),
        "categories": Resource.CATEGORY_CHOICES,
        "destinations": Resource.DESTINATION_CHOICES,
        "selected_cat": category,
        "selected_dest": destination,
        "selected_filtre": filtre,
        "has_premium": has_premium,
        "purchased_ids": purchased_ids,
        "featured": featured,
    }
    return render(request, "resources/library.html", context)


def resource_detail(request, pk, slug=None):
    resource = get_object_or_404(Resource, pk=pk, is_active=True)

    has_premium = request.user.is_authenticated and has_candidate_access(request.user)
    has_purchased = (
        request.user.is_authenticated
        and ResourcePurchase.objects.filter(
            user=request.user, resource=resource, is_active=True
        ).exists()
    )
    can_download = _user_has_access(request.user, resource)

    related = (
        Resource.objects.filter(is_active=True, category=resource.category)
        .exclude(pk=resource.pk)[:4]
    )

    context = {
        "resource": resource,
        "has_premium": has_premium,
        "has_purchased": has_purchased,
        "can_download": can_download,
        "related": related,
        "what_inside": resource.get_what_inside_list(),
        "whatsapp_url": resource.whatsapp_buy_url(WHATSAPP_NUMBER),
    }
    return render(request, "resources/detail.html", context)


def download(request, pk):
    resource = get_object_or_404(Resource, pk=pk, is_active=True)

    if not resource.file:
        raise Http404

    if not _user_has_access(request.user, resource):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('authentification:login')}?next={request.path}")
        messages.error(request, "🔒 Accès requis pour télécharger cette ressource.")
        if resource.is_paid():
            return redirect(reverse("resources:detail", args=[resource.pk]))
        return redirect(f"{reverse('billing:pricing')}?next={request.path}")

    file_path = resource.file.path
    if not os.path.exists(file_path):
        raise Http404

    Resource.objects.filter(pk=resource.pk).update(downloads=resource.downloads + 1)

    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or "application/octet-stream"
    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
