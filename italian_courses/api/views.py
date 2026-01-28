from __future__ import annotations

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from italian_courses.models import CourseCategory, Lesson

# DRF endpoints (optional)
def drf_available() -> bool:
    try:
        import rest_framework  # type: ignore
        return True
    except Exception:
        return False

@require_GET
def health(request):
    return JsonResponse({"ok": True, "drf": drf_available()})

@require_GET
def categories(request):
    data = list(CourseCategory.objects.values("id", "name", "slug"))
    return JsonResponse({"results": data})

@require_GET
def lessons(request):
    # Simple JSON API without DRF (works always)
    category = request.GET.get("category")
    qs = Lesson.objects.filter(is_published=True).select_related("category")
    if category:
        qs = qs.filter(category__slug=category)

    data = []
    for l in qs.order_by("category__name", "order_index"):
        data.append({
            "id": l.id,
            "title": l.title,
            "slug": l.slug,
            "excerpt": l.excerpt,
            "level": l.level,
            "order_index": l.order_index,
            "category": {"name": l.category.name, "slug": l.category.slug},
            "cover_image": l.cover_image.url if l.cover_image else None,
        })
    return JsonResponse({"results": data})
