import mimetypes
import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from .models import Resource


def library(request):
    resources = Resource.objects.filter(is_active=True)
    total = resources.count()
    context = {
        "resources": resources,
        "total": total,
        "categories": Resource.CATEGORY_CHOICES,
    }
    return render(request, "resources/library.html", context)


def download(request, pk):
    resource = get_object_or_404(Resource, pk=pk, is_active=True)

    if not resource.file:
        raise Http404

    if resource.is_premium and not request.user.is_authenticated:
        raise Http404

    file_path = resource.file.path
    if not os.path.exists(file_path):
        raise Http404

    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or "application/octet-stream"

    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
