"""
e_shelle_ai/views.py
Vues de l'agent IA central E-Shelle.
"""
import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import (
    StreamingHttpResponse, JsonResponse, HttpResponseForbidden
)
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import models
from django.db.models import Count, Sum
from django.utils import timezone

from .models import AIConversation, AIMessage, AIQuota, CentralAgentQueryLog
from .services.openai_service import EshelleAIService
from .services.context_builder import UserContextBuilder
from .services.memory_service import MemoryService
from .services.quota_service import QuotaService

logger = logging.getLogger(__name__)

# Rate limiting simple en cache Django (sans dépendance externe)
from django.core.cache import cache

RATE_LIMIT_WINDOW = 60       # secondes
RATE_LIMIT_MAX    = 30       # requêtes max par fenêtre


@staff_member_required
def admin_dashboard(request):
    """Dashboard staff pour piloter l'Agent IA central."""
    since = timezone.now() - timezone.timedelta(days=30)
    logs = CentralAgentQueryLog.objects.filter(created_at__gte=since)

    total_queries = logs.count()
    without_results = logs.filter(had_results=False).count()
    premium_results = logs.aggregate(total=Sum("premium_results_count"))["total"] or 0
    conversion_rate = round(((total_queries - without_results) / total_queries) * 100, 1) if total_queries else 0

    module_stats = (
        logs.values("module")
        .annotate(
            total=Count("id"),
            empty=Count("id", filter=models.Q(had_results=False)),
            premium=Sum("premium_results_count"),
        )
        .order_by("-total")[:12]
    )
    top_queries = logs.values("query", "module").annotate(total=Count("id")).order_by("-total", "query")[:15]
    no_result_queries = (
        logs.filter(had_results=False)
        .values("query", "module")
        .annotate(total=Count("id"))
        .order_by("-total", "query")[:15]
    )

    try:
        from business.models import BusinessLeadEvent, BusinessProfile

        top_businesses = BusinessProfile.objects.order_by("-leads_count", "-views_count")[:10]
        lead_stats = (
            BusinessLeadEvent.objects.filter(created_at__gte=since)
            .values("event_type", "source")
            .annotate(total=Count("id"))
            .order_by("-total")[:12]
        )
    except Exception:
        top_businesses = []
        lead_stats = []

    return render(
        request,
        "e_shelle_ai/admin_dashboard.html",
        {
            "total_queries": total_queries,
            "without_results": without_results,
            "premium_results": premium_results,
            "conversion_rate": conversion_rate,
            "module_stats": module_stats,
            "top_queries": top_queries,
            "no_result_queries": no_result_queries,
            "top_businesses": top_businesses,
            "lead_stats": lead_stats,
        },
    )


def _check_rate_limit(user_id: int) -> bool:
    """True si l'utilisateur est dans les limites. False = rate limited."""
    key = f"ai_rl_{user_id}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT_MAX:
        return False
    cache.set(key, count + 1, RATE_LIMIT_WINDOW)
    return True


# ─── Chat principal ───────────────────────────────────────────────────────────

class ChatView(LoginRequiredMixin, View):
    """Page /ai/ — Interface chat principale."""

    def get(self, request, conversation_id=None):
        user = request.user

        # Toutes les conversations de l'utilisateur
        conversations = AIConversation.objects.filter(
            user=user, is_active=True
        ).order_by("-updated_at")[:50]

        # Conversation active
        active_conv = None
        messages_list = []
        if conversation_id:
            active_conv = get_object_or_404(AIConversation, pk=conversation_id, user=user)
            messages_list = active_conv.messages.filter(
                role__in=["user", "assistant"]
            ).order_by("created_at")[:100]
        elif conversations.exists():
            active_conv   = conversations.first()
            messages_list = active_conv.messages.filter(
                role__in=["user", "assistant"]
            ).order_by("created_at")[:100]

        # Quota
        quota_info = QuotaService().get_remaining(user)

        return render(request, "e_shelle_ai/chat.html", {
            "conversations": conversations,
            "active_conv":   active_conv,
            "messages":      messages_list,
            "quota":         quota_info,
        })


class ConversationLoadView(LoginRequiredMixin, View):
    """GET /ai/c/<id>/ — Charge une conversation spécifique."""

    def get(self, request, pk):
        return ChatView().get(request, conversation_id=pk)


# ─── API Chat (Streaming SSE) ─────────────────────────────────────────────────

class ChatAPIView(LoginRequiredMixin, View):
    """
    POST /ai/api/chat/
    Body JSON: {"message": "...", "conversation_id": null|int}
    Retourne: StreamingHttpResponse au format SSE
    """

    def post(self, request):
        user = request.user

        # Rate limiting
        if not _check_rate_limit(user.id):
            return JsonResponse(
                {"error": "Trop de requêtes. Attendez 1 minute avant de réessayer."},
                status=429
            )

        # Parse du body
        try:
            data    = json.loads(request.body)
            message = data.get("message", "").strip()
            conv_id = data.get("conversation_id")
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Format de requête invalide."}, status=400)

        if not message:
            return JsonResponse({"error": "Message vide."}, status=400)

        # Quota check
        quota_service = QuotaService()
        if not quota_service.check_message_quota(user):
            upgrade_msg = quota_service.get_upgrade_message(user, "message")
            return JsonResponse({"error": upgrade_msg, "quota_exceeded": True}, status=402)

        # Conversation
        conv = self._get_or_create_conversation(user, conv_id, message)

        # Sauvegarder le message utilisateur
        AIMessage.objects.create(
            conversation=conv,
            role="user",
            content=message,
            message_type="text",
        )

        # Construire le contexte
        context_builder = UserContextBuilder()
        user_context    = context_builder.build(user)
        system_prompt   = context_builder.build_system_prompt(user_context)

        # Historique pour GPT
        history = conv.get_context_messages(limit=18)

        def stream_response():
            """Générateur SSE — envoie la réponse chunk par chunk."""
            ai_service  = EshelleAIService()
            full_reply  = ""
            conv_id_val = conv.pk

            # Envoi du conv_id au client immédiatement
            yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv_id_val})}\n\n"

            try:
                for chunk in ai_service.chat_stream(history, system_prompt, user=user):
                    full_reply += chunk
                    payload = json.dumps({"type": "chunk", "text": chunk})
                    yield f"data: {payload}\n\n"

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'text': 'Erreur technique.'})}\n\n"
                full_reply = "Erreur technique."

            finally:
                # Sauvegarder la réponse complète
                if full_reply:
                    AIMessage.objects.create(
                        conversation=conv,
                        role="assistant",
                        content=full_reply,
                        message_type="text",
                    )
                    # Incrémenter quota
                    quota_service.increment_usage(user, "message")
                    # Mise à jour mémoire
                    mem_service = MemoryService()
                    mem_service.update_memory_from_message(user, message, full_reply)
                    mem_service.summarize_if_needed(user)

                # Signal fin de stream
                quota_remaining = quota_service.get_remaining(user)
                yield f"data: {json.dumps({'type': 'done', 'quota': quota_remaining})}\n\n"

        response = StreamingHttpResponse(
            stream_response(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"  # Nginx : désactiver le buffering
        return response

    def _get_or_create_conversation(self, user, conv_id, first_message: str):
        """Récupère ou crée une conversation."""
        if conv_id:
            try:
                return AIConversation.objects.get(pk=conv_id, user=user)
            except AIConversation.DoesNotExist:
                pass

        # Nouvelle conversation avec titre auto
        ai_service = EshelleAIService()
        title = ai_service.generate_title(first_message)
        conv = AIConversation.objects.create(
            user=user,
            title=title,
            module_context=self._detect_module(first_message),
        )
        return conv

    def _detect_module(self, message: str) -> str:
        """Détecte le module E-Shelle concerné par le message."""
        m = message.lower()
        mapping = {
            "resto":      ["restaurant", "plat", "manger", "cuisine", "menu"],
            "boutique":   ["boutique", "produit", "vente", "commander"],
            "pressing":   ["pressing", "blanchisserie", "vêtement"],
            "gaz":        ["gaz", "bouteille", "butane"],
            "pharma":     ["pharmacie", "médicament", "santé"],
            "marketing":  ["marketing", "vendre", "facebook", "instagram", "client", "pub"],
            "formations": ["formation", "cours", "apprendre"],
        }
        for key, keywords in mapping.items():
            if any(kw in m for kw in keywords):
                return key
        return "global"


# ─── Génération d'image ───────────────────────────────────────────────────────

class GenerateImageView(LoginRequiredMixin, View):
    """
    POST /ai/api/image/
    Body JSON: {"prompt": "...", "context": "food|product|banner|logo|social_media"}
    """

    def post(self, request):
        user = request.user

        # Quota image
        quota_service = QuotaService()
        if not quota_service.check_image_quota(user):
            upgrade_msg = quota_service.get_upgrade_message(user, "image")
            return JsonResponse({"error": upgrade_msg, "quota_exceeded": True}, status=402)

        try:
            data    = json.loads(request.body)
            prompt  = data.get("prompt", "").strip()
            context = data.get("context", "general")
            conv_id = data.get("conversation_id")
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Format invalide."}, status=400)

        if not prompt:
            return JsonResponse({"error": "Prompt vide."}, status=400)

        # Sanitisation basique
        prompt = prompt[:500]
        context = context if context in ["food", "product", "banner", "logo", "social_media", "portrait", "general"] else "general"

        ai_service = EshelleAIService()
        result = ai_service.generate_image(prompt, context, user=user)

        if result.get("error"):
            return JsonResponse({
                "error": f"Génération image indisponible : {result['error']}",
                "adgen_url": "/pub/",
            })

        # Incrémenter quota
        quota_service.increment_usage(user, "image")

        # Sauvegarder dans le message de conversation si conv_id fourni
        if conv_id:
            try:
                conv = AIConversation.objects.get(pk=conv_id, user=user)
                AIMessage.objects.create(
                    conversation=conv,
                    role="assistant",
                    content=f"Image générée : {prompt}",
                    message_type="image",
                    image_url=result.get("media_url", ""),
                )
            except Exception:
                pass

        return JsonResponse({
            "image_url":       result.get("media_url", ""),
            "enhanced_prompt": result.get("enhanced_prompt", ""),
            "quota":           quota_service.get_remaining(user),
        })


# ─── Gestion des conversations ────────────────────────────────────────────────

class NewConversationView(LoginRequiredMixin, View):
    """POST /ai/conversations/new/ — Crée une nouvelle conversation vide."""

    def post(self, request):
        conv = AIConversation.objects.create(
            user=request.user,
            title="Nouvelle conversation",
        )
        return JsonResponse({"conversation_id": conv.pk, "title": conv.title})


class DeleteConversationView(LoginRequiredMixin, View):
    """POST /ai/conversations/<pk>/delete/ — Supprime (soft) une conversation."""

    def post(self, request, pk):
        conv = get_object_or_404(AIConversation, pk=pk, user=request.user)
        conv.is_active = False
        conv.save(update_fields=["is_active"])
        return JsonResponse({"success": True})


class ConversationListView(LoginRequiredMixin, View):
    """GET /ai/conversations/ — Liste JSON des conversations."""

    def get(self, request):
        convs = AIConversation.objects.filter(
            user=request.user, is_active=True
        ).order_by("-updated_at")[:50]

        data = [
            {
                "id":      c.pk,
                "title":   c.title,
                "module":  c.module_context,
                "updated": c.updated_at.strftime("%d/%m/%Y %H:%M"),
                "count":   c.message_count,
            }
            for c in convs
        ]
        return JsonResponse({"conversations": data})


class ClearMemoryView(LoginRequiredMixin, View):
    """POST /ai/memory/clear/ — Efface la mémoire long terme de l'utilisateur."""

    def post(self, request):
        MemoryService().clear_memory(request.user)
        return JsonResponse({"success": True, "message": "Mémoire effacée."})


class QuotaStatusView(LoginRequiredMixin, View):
    """GET /ai/quota/ — Retourne le quota actuel de l'utilisateur."""

    def get(self, request):
        quota = QuotaService().get_remaining(request.user)
        return JsonResponse(quota)
