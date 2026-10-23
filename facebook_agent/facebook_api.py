"""
Client Meta Graph API pour E-Shelle Auto-Post.
Gère la publication, la récupération de stats et le refresh de token.
"""

import requests
import logging
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger("facebook_agent")

GRAPH_API_BASE = "https://graph.facebook.com/v25.0"


class FacebookAPIError(Exception):
    """Erreur levée lors d'une réponse d'erreur de l'API Facebook."""
    def __init__(self, message: str, code: int = 0, fb_error: dict = None):
        super().__init__(message)
        self.code = code
        self.fb_error = fb_error or {}


class FacebookAPIClient:
    """
    Client complet pour l'API Graph Meta.
    Supporte: publication texte, photo, lien, stats, token refresh.
    """

    def __init__(self, page_access_token: str, page_id: str, app_id: str = "", app_secret: str = ""):
        self.token = page_access_token
        self.page_id = page_id
        self.app_id = app_id
        self.app_secret = app_secret
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "E-Shelle-AutoPost/1.0"})

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        data: dict = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        url = f"{GRAPH_API_BASE}/{endpoint}"
        params = params or {}
        params["access_token"] = self.token

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=data if method.upper() == "POST" else None,
                data=data if method.upper() == "POST" and not isinstance(data, dict) else None,
                timeout=timeout,
            )
            result = response.json()

            if "error" in result:
                err = result["error"]
                raise FacebookAPIError(
                    message=err.get("message", "Erreur inconnue"),
                    code=err.get("code", 0),
                    fb_error=err,
                )
            return result

        except requests.exceptions.Timeout:
            raise FacebookAPIError("Timeout: l'API Facebook n'a pas répondu à temps")
        except requests.exceptions.ConnectionError:
            raise FacebookAPIError("Erreur de connexion à l'API Facebook")
        except requests.exceptions.JSONDecodeError:
            raise FacebookAPIError("Réponse invalide de l'API Facebook (non-JSON)")

    # ------------------------------------------------------------------ #
    # Publication                                                          #
    # ------------------------------------------------------------------ #

    def publish_text_post(self, message: str) -> Dict[str, Any]:
        """Publie un post texte simple sur la page."""
        logger.info(f"[FacebookAPI] Publication texte sur page {self.page_id}")
        result = self._request(
            "POST",
            f"{self.page_id}/feed",
            data={"message": message},
        )
        logger.info(f"[FacebookAPI] Post publié: {result.get('id')}")
        return result

    def publish_link_post(self, message: str, link: str) -> Dict[str, Any]:
        """Publie un post avec lien (aperçu automatique)."""
        logger.info(f"[FacebookAPI] Publication lien sur page {self.page_id}")
        result = self._request(
            "POST",
            f"{self.page_id}/feed",
            data={"message": message, "link": link},
        )
        return result

    def publish_comment(self, post_id: str, message: str) -> Dict[str, Any]:
        """Publish a first comment under a Page post (requires Page permissions)."""
        if not post_id or not message:
            raise ValueError("Un ID de publication et un commentaire sont requis.")
        try:
            response = self.session.post(
                f"{GRAPH_API_BASE}/{post_id}/comments",
                data={"message": message, "access_token": self.token},
                timeout=30,
            )
            result = response.json()
            if "error" in result:
                error = result["error"]
                raise FacebookAPIError(
                    message=error.get("message", "Erreur inconnue"),
                    code=error.get("code", 0), fb_error=error,
                )
            return result
        except requests.exceptions.Timeout as exc:
            raise FacebookAPIError("Timeout pendant la publication du commentaire") from exc
        except requests.exceptions.ConnectionError as exc:
            raise FacebookAPIError("Erreur de connexion pendant la publication du commentaire") from exc
        except requests.exceptions.JSONDecodeError as exc:
            raise FacebookAPIError("Réponse invalide de Meta pendant la publication du commentaire") from exc

    def publish_photo_post(self, message: str, image_url: str) -> Dict[str, Any]:
        """Publie un post avec une image depuis une URL."""
        logger.info(f"[FacebookAPI] Publication photo sur page {self.page_id}")

        # Étape 1 : Upload de la photo (non publiée)
        photo_result = self._request(
            "POST",
            f"{self.page_id}/photos",
            data={"url": image_url, "published": False},
        )
        photo_id = photo_result.get("id")

        # Étape 2 : Publier le post avec la photo attachée
        result = self._request(
            "POST",
            f"{self.page_id}/feed",
            data={
                "message": message,
                "attached_media": [{"media_fbid": photo_id}],
            },
        )
        return result

    def publish_post(
        self,
        message: str,
        image_url: str = "",
        link_url: str = "",
    ) -> Dict[str, Any]:
        """Point d'entrée unifié — choisit automatiquement le type de post."""
        if image_url:
            return self.publish_photo_post(message, image_url)
        elif link_url:
            return self.publish_link_post(message, link_url)
        else:
            return self.publish_text_post(message)

    # ------------------------------------------------------------------ #
    # Statistiques                                                         #
    # ------------------------------------------------------------------ #

    def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Récupère les statistiques d'un post (likes, commentaires, partages)."""
        try:
            result = self._request(
                "GET",
                post_id,
                params={"fields": "likes.summary(true),comments.summary(true),shares,reactions.summary(true)"},
            )
            return {
                "likes": result.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": result.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares": result.get("shares", {}).get("count", 0),
                "reactions": result.get("reactions", {}).get("summary", {}).get("total_count", 0),
            }
        except FacebookAPIError as e:
            logger.warning(f"[FacebookAPI] Impossible de récupérer les stats du post {post_id}: {e}")
            return {"likes": 0, "comments": 0, "shares": 0, "reactions": 0}

    def get_page_insights(self) -> Dict[str, Any]:
        """Récupère les statistiques globales de la page."""
        try:
            result = self._request(
                "GET",
                f"{self.page_id}",
                params={"fields": "id,fan_count,followers_count,name,category"},
            )
            return result
        except FacebookAPIError as e:
            logger.error(f"[FacebookAPI] Erreur insights page: {e}")
            return {}

    def get_recent_posts(self, limit: int = 10) -> list:
        """Récupère les derniers posts de la page."""
        try:
            result = self._request(
                "GET",
                f"{self.page_id}/feed",
                params={
                    "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
                    "limit": limit,
                },
            )
            return result.get("data", [])
        except FacebookAPIError as e:
            logger.error(f"[FacebookAPI] Erreur récupération posts: {e}")
            return []

    # ------------------------------------------------------------------ #
    # Gestion du token                                                     #
    # ------------------------------------------------------------------ #

    def verify_token(self) -> Dict[str, Any]:
        """Vérifie la validité et les détails du token actuel."""
        app_id = self.app_id or getattr(settings, "FACEBOOK_APP_ID", "")
        app_secret = self.app_secret or getattr(settings, "FACEBOOK_APP_SECRET", "")

        if not app_id or not app_secret:
            logger.warning("[FacebookAPI] APP_ID ou APP_SECRET manquant pour vérifier le token")
            return {"is_valid": False, "expires_at": None, "error": "Meta App ID/Secret non configurés"}

        try:
            response = requests.get(
                f"{GRAPH_API_BASE}/debug_token",
                params={
                    "input_token": self.token,
                    "access_token": f"{app_id}|{app_secret}",
                },
                timeout=15,
            )
            data = response.json().get("data", {})
            return {
                "is_valid": data.get("is_valid", False),
                "expires_at": data.get("expires_at"),
                "scopes": data.get("scopes", []),
                "app_id": data.get("app_id"),
            }
        except Exception as e:
            logger.error(f"[FacebookAPI] Erreur vérification token: {e}")
            return {"is_valid": False, "expires_at": None}

    def exchange_for_long_lived_token(self, short_lived_token: str) -> Optional[str]:
        """Échange un token court (1h) contre un token longue durée (60j)."""
        app_id = getattr(settings, "FACEBOOK_APP_ID", "")
        app_secret = getattr(settings, "FACEBOOK_APP_SECRET", "")

        if not app_id or not app_secret:
            logger.error("[FacebookAPI] APP_ID ou APP_SECRET requis pour l'échange de token")
            return None

        try:
            response = requests.get(
                f"{GRAPH_API_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": short_lived_token,
                },
                timeout=15,
            )
            data = response.json()
            if "access_token" in data:
                return data["access_token"]
            logger.error(f"[FacebookAPI] Réponse inattendue lors de l'échange: {data}")
            return None
        except Exception as e:
            logger.error(f"[FacebookAPI] Erreur échange token: {e}")
            return None

    def get_page_token_from_user_token(self, user_token: str) -> Optional[str]:
        """Récupère le token de page permanent à partir d'un token utilisateur."""
        try:
            result = requests.get(
                f"{GRAPH_API_BASE}/me/accounts",
                params={"access_token": user_token},
                timeout=15,
            ).json()
            for page in result.get("data", []):
                if page.get("id") == self.page_id:
                    return page.get("access_token")
            logger.warning(f"[FacebookAPI] Page {self.page_id} non trouvée dans les comptes")
            return None
        except Exception as e:
            logger.error(f"[FacebookAPI] Erreur récupération token page: {e}")
            return None
