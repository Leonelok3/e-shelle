from django.shortcuts import render
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
