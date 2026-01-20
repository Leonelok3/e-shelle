from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Session
from .serializers import SessionCreateSerializer, AnswersPatchSerializer, ScoreSerializer


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_session(request):
    ser = SessionCreateSerializer(data=request.data, context={"request": request})
    ser.is_valid(raise_exception=True)
    sess = ser.save()
    return Response(
        {"id": sess.id, "locale": sess.locale, "source": sess.source},
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def patch_answers(request, session_id: int):
    try:
        sess = Session.objects.get(id=session_id, user=request.user)
    except Session.DoesNotExist:
        return Response({"detail": "No Session matches the given query."}, status=status.HTTP_404_NOT_FOUND)

    ser = AnswersPatchSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    patch = ser.validated_data
    data = sess.answers_json or {}
    data.update(patch)

    sess.answers_json = data
    sess.save(update_fields=["answers_json", "updated_at"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def compute_score(request, session_id: int):
    """
    Remplit result_json.
    Pour l’instant: on met un exemple (TEST) pour que ton front affiche un programme.
    """
    try:
        sess = Session.objects.get(id=session_id, user=request.user)
    except Session.DoesNotExist:
        return Response({"detail": "No Session matches the given query."}, status=status.HTTP_404_NOT_FOUND)

    ser = ScoreSerializer(data=request.data or {})
    ser.is_valid(raise_exception=True)
    country = (ser.validated_data.get("country") or "").strip() or "Canada"

    # ✅ EXEMPLE (remplace plus tard par ton vrai moteur)
    sess.result_json = {
        "country": country,
        "results": [
            {
                "title": "Programme de test – Entrée Express",
                "country": country,
                "score": 72,
                "eligible": True,
                "url_official": "https://www.canada.ca/",
                "checklist": {
                    "documents": [
                        {"label": "Passeport", "required": True},
                        {"label": "Diplômes", "required": True},
                        {"label": "Preuves d’expérience", "required": False},
                    ],
                    "steps": [
                        {"label": "Créer un profil", "eta_days": 2},
                        {"label": "Soumettre les documents", "eta_days": 14},
                        {"label": "Attendre la réponse", "eta_days": 60},
                    ],
                },
                "citations": [
                    {"title": "Site officiel Canada", "url": "https://www.canada.ca/"},
                ],
            }
        ],
    }

    sess.save(update_fields=["result_json", "updated_at"])
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_result(request, session_id: int):
    """
    Retourne toujours un JSON propre:
    - result_json vide => renvoie {"results": []}
    - result_json sans clé results => ajoute results=[]
    """
    try:
        sess = Session.objects.get(id=session_id, user=request.user)
    except Session.DoesNotExist:
        return Response({"detail": "No Session matches the given query."}, status=status.HTTP_404_NOT_FOUND)

    data = sess.result_json or {}
    if "results" not in data:
        data["results"] = []
    return Response(data)
