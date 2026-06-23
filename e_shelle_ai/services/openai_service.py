"""
e_shelle_ai/services/openai_service.py
Service principal GPT-4o + DALL-E 3 pour E-Shelle AI.
Gère le streaming SSE, l'injection de contexte et les logs API.
"""
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)

# Nombre max de messages gardés dans le contexte (évite les coûts excessifs)
MAX_CONTEXT_MESSAGES = getattr(settings, "AI_MAX_CONTEXT_MESSAGES", 20)


class EshelleAIService:
    """Service IA central — chat streaming + génération d'images."""

    def __init__(self):
        self.api_key = getattr(settings, "OPENAI_API_KEY", "")
        self.client = None
        if self.api_key:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        self.chat_model  = getattr(settings, "OPENAI_CHAT_MODEL",  "gpt-4o")
        self.image_model = getattr(settings, "OPENAI_IMAGE_MODEL", "dall-e-3")

    # ─── Chat ─────────────────────────────────────────────────────────────

    def chat_stream(self, messages: list, system_prompt: str, user=None):
        """
        Envoie la conversation à GPT-4o en mode streaming.
        Yield des chunks de texte au fur et à mesure.

        Args:
            messages:      Liste [{role, content}] — historique + nouveau message
            system_prompt: Prompt système construit par UserContextBuilder
            user:          Utilisateur Django (pour les logs)

        Yields:
            str — Chunks de texte de la réponse
        """
        full_messages = [{"role": "system", "content": system_prompt}]

        # Enrichissement avec recherche interne si nécessaire
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        internal_data = self._get_internal_context(last_user_msg)
        if internal_data:
            full_messages.append({
                "role": "system",
                "content": f"Données E-Shelle pertinentes pour cette question :\n{internal_data}"
            })

        # Enrichissement marketing si pertinent
        marketing_data = self._get_marketing_context(last_user_msg)
        if marketing_data:
            full_messages.append({
                "role": "system",
                "content": f"Base de connaissances marketing :\n{marketing_data}"
            })

        full_messages.extend(messages[-MAX_CONTEXT_MESSAGES:])

        prompt_tokens = 0
        completion_tokens = 0
        full_response = ""

        if not self.client:
            yield from self._central_agent_fallback(last_user_msg, messages, user=user)
            return

        try:
            stream = self.client.chat.completions.create(
                model=self.chat_model,
                messages=full_messages,
                stream=True,
                max_tokens=1500,
                temperature=0.7,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    text = delta.content
                    full_response += text
                    yield text

            # Estimation des tokens (approximation pour le streaming)
            prompt_tokens     = sum(len(m["content"]) // 4 for m in full_messages)
            completion_tokens = len(full_response) // 4

        except Exception as e:
            logger.error(f"GPT-4o stream error: {e}")
            error_msg = (
                "Désolé, une erreur technique s'est produite. "
                "Veuillez réessayer dans quelques instants. "
                f"Si le problème persiste, contactez le support E-Shelle."
            )
            yield error_msg
            full_response = error_msg

        finally:
            # Log de l'appel API
            self._log_api_call(
                user=user,
                type_appel="chat",
                model=self.chat_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                success=bool(full_response and "erreur technique" not in full_response),
            )

    def chat_simple(self, messages: list, system_prompt: str, user=None) -> str:
        """
        Version non-streaming pour les appels internes (résumé mémoire, etc.).
        Retourne la réponse complète.
        """
        full_messages = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages[-MAX_CONTEXT_MESSAGES:])

        if not self.client:
            return self._central_agent_text(messages, user=user)

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=full_messages,
                max_tokens=1000,
                temperature=0.7,
            )
            content = response.choices[0].message.content
            usage   = response.usage

            self._log_api_call(
                user=user,
                type_appel="chat",
                model=self.chat_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            )
            return content

        except Exception as e:
            logger.error(f"GPT-4o simple error: {e}")
            return ""

    def generate_title(self, first_message: str) -> str:
        """Génère un titre court pour une nouvelle conversation."""
        if not self.client:
            return first_message[:50] + "…" if len(first_message) > 50 else first_message
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Génère un titre court (4-6 mots, en français) "
                            f"pour une conversation qui commence par : '{first_message[:100]}'"
                            f"\nRéponds uniquement avec le titre, sans guillemets ni ponctuation finale."
                        )
                    }
                ],
                max_tokens=20,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return first_message[:50] + "…" if len(first_message) > 50 else first_message

    # ─── Image ────────────────────────────────────────────────────────────

    def generate_image(self, prompt: str, context: str = "general", user=None) -> dict:
        """
        Génère une image avec Google Imagen 3 ou DALL-E 3.
        """
        if getattr(settings, "GOOGLE_API_KEY", ""):
            from e_shelle_ai.services.tools.google_media_generator import generate_google_image
            result = generate_google_image(prompt, context)
            if not result.get("error"):
                # Log
                self._log_api_call(
                    user=user,
                    type_appel="image",
                    model="imagen-3.0",
                    prompt_tokens=0,
                    completion_tokens=0,
                    success=True,
                )
                return result

        if not self.client:
            return {
                "image_url": "",
                "local_path": "",
                "enhanced_prompt": prompt,
                "error": "Clé API non configurée. Veuillez ajouter GOOGLE_API_KEY dans votre fichier .env pour générer des images.",
            }
        from e_shelle_ai.services.tools.image_generator import generate_image
        result = generate_image(prompt, context, save_locally=True)

        # Log
        self._log_api_call(
            user=user,
            type_appel="image",
            model=self.image_model,
            prompt_tokens=0,
            completion_tokens=0,
            success=not bool(result.get("error")),
            error_message=result.get("error", ""),
        )
        return result

    # ─── Helpers internes ─────────────────────────────────────────────────

    def _central_agent_fallback(self, last_user_msg: str, messages: list, user=None):
        response = self._central_agent_route(last_user_msg, messages, user=user)
        text = response.get("message") or "Je t'oriente vers le bon espace E-Shelle."
        if response.get("redirect_label") and response.get("redirect_url"):
            text += f"\n\n👉 {response['redirect_label']} : {response['redirect_url']}"
        if response.get("results"):
            lines = []
            for item in response["results"][:4]:
                title = item.get("title", "Résultat")
                detail = item.get("details") or item.get("subtitle") or ""
                action = item.get("primary_url") or item.get("url") or ""
                lines.append(f"- {title} — {detail} {action}".strip())
            text += "\n\nSuggestions E-Shelle:\n" + "\n".join(lines)
        yield text

    def _central_agent_text(self, messages: list, user=None) -> str:
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        response = self._central_agent_route(last_user_msg, messages, user=user)
        return response.get("message", "")

    def _central_agent_route(self, last_user_msg: str, messages: list, user=None) -> dict:
        from e_shelle_ai.services.central_agent import route_message

        history = [
            {"role": msg.get("role"), "content": msg.get("content")}
            for msg in messages
            if msg.get("role") in {"user", "assistant"} and msg.get("content")
        ]
        return route_message(last_user_msg, history, user=user)

    def _get_internal_context(self, query: str) -> str:
        """Recherche dans la base E-Shelle si la question est pertinente."""
        try:
            from e_shelle_ai.services.tools.search_internal import search_eshelle
            return search_eshelle(query)
        except Exception:
            return ""

    def _get_marketing_context(self, query: str) -> str:
        """Injecte les connaissances marketing si la question le demande."""
        try:
            marketing_keywords = [
                "vendre", "marketing", "client", "facebook", "instagram",
                "tiktok", "whatsapp", "pub", "publicité", "croissance",
                "ia", "automatisation", "prix", "tarif", "fidél",
                "réseaux", "seo", "google", "mobile money", "paiement"
            ]
            if any(kw in query.lower() for kw in marketing_keywords):
                from e_shelle_ai.services.tools.marketing_advisor import get_marketing_advice
                return get_marketing_advice(query)
        except Exception:
            pass
        return ""

    def _log_api_call(self, user, type_appel: str, model: str,
                      prompt_tokens: int, completion_tokens: int,
                      success: bool = True, error_message: str = ""):
        """Enregistre l'appel API dans AILog."""
        try:
            from e_shelle_ai.models import AILog
            total = prompt_tokens + completion_tokens
            cout  = AILog.compute_cost(prompt_tokens, completion_tokens, model)

            AILog.objects.create(
                user=user,
                type_appel=type_appel,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total,
                cout_estime_usd=cout,
                model_used=model,
                success=success,
                error_message=error_message[:500] if error_message else "",
            )
        except Exception as e:
            logger.debug(f"AILog creation error: {e}")
