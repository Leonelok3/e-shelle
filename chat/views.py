import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .models import ConversationSession, Message
from .services import route_message


def get_or_create_session(request):
    """Recupere ou cree une session de conversation."""
    if request.user.is_authenticated:
        session, _ = ConversationSession.objects.get_or_create(user=request.user)
        return session

    if not request.session.session_key:
        request.session.create()
    session, _ = ConversationSession.objects.get_or_create(
        session_key=request.session.session_key
    )
    return session


def chat_view(request):
    """Page principale du chat universel."""
    session = get_or_create_session(request)
    messages = session.messages.all()
    return render(request, "chat/chat.html", {"messages": messages, "session": session})


@require_http_methods(["POST"])
def send_message(request):
    """Recoit un message, appelle le routeur IA, sauvegarde et retourne la reponse."""
    try:
        data = json.loads(request.body or "{}")
        user_input = data.get("message", "").strip()

        if not user_input or len(user_input) > 1000:
            return JsonResponse({"error": "Message invalide"}, status=400)

        session = get_or_create_session(request)
        Message.objects.create(session=session, role="user", content=user_input)

        history = list(session.messages.values("role", "content").order_by("created_at"))
        ai_response = route_message(user_input, history)

        ai_message = Message.objects.create(
            session=session,
            role="assistant",
            content=ai_response.get("message", ""),
            module_detected=ai_response.get("module", "general"),
            redirect_url=ai_response.get("redirect_url", "/"),
            results=ai_response.get("results", []),
            has_image=bool(ai_response.get("image_url")),
            image_url=ai_response.get("image_url", ""),
        )

        return JsonResponse(
            {
                "message": ai_message.content,
                "module": ai_message.module_detected,
                "redirect": ai_response.get("redirect", False),
                "redirect_url": ai_message.redirect_url,
                "redirect_label": ai_response.get("redirect_label", ""),
                "image_url": ai_message.image_url,
                "results": ai_message.results,
            }
        )
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@require_http_methods(["POST"])
def clear_session(request):
    """Efface l'historique de la conversation."""
    session = get_or_create_session(request)
    session.messages.all().delete()
    return JsonResponse({"status": "cleared"})

# Create your views here.
