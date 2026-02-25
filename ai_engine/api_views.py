import json
import traceback

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ai_engine.services.generation_orchestrator import generate_and_insert


@csrf_exempt
def generate_content_api(request):
    if request.method == "GET":
        return JsonResponse(
            {
                "ok": True,
                "message": "Use POST with JSON body: skill, language, level.",
                "example": {"skill": "CE", "language": "fr", "level": "A1"},
            },
            status=200,
        )

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    skill = payload.get("skill")
    language = payload.get("language")
    level = payload.get("level")

    if not skill or not language or not level:
        return JsonResponse(
            {"error": "Missing required fields: skill, language, level."},
            status=400,
        )

    try:
        result = generate_and_insert(skill=skill, language=language, level=level)
        return JsonResponse({"ok": True, "result": result}, status=200)
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except Exception as e:
        if settings.DEBUG:
            return JsonResponse(
                {"ok": False, "error": str(e), "traceback": traceback.format_exc()},
                status=500,
            )
        return JsonResponse({"ok": False, "error": "Internal server error."}, status=500)