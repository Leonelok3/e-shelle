from django.http import JsonResponse

def health(request):
    return JsonResponse({
        "ok": True,
        "service": "radar",
        "message": "Radar API is running (stub)."
    })
