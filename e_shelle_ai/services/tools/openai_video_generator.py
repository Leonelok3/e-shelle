import base64
import logging
import os
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


OPENAI_VIDEO_API_BASE = "https://api.openai.com/v1"


def _response_error(response, fallback):
    try:
        payload = response.json()
    except ValueError:
        return fallback
    error = payload.get("error")
    if isinstance(error, dict):
        return error.get("message") or fallback
    if isinstance(error, str):
        return error
    return fallback


def _headers():
    api_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None, "OPENAI_API_KEY n'est pas configurée."
    return {"Authorization": f"Bearer {api_key}"}, None


def _normalize_seconds(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        seconds = 8
    if seconds <= 4:
        return 4
    if seconds <= 8:
        return 8
    return 12


def start_openai_video(prompt: str, size: str = "1280x720", image_b64: str | None = None, seconds: int = 8) -> dict:
    """Start an OpenAI Sora video job and return a provider-scoped operation name."""
    headers, error = _headers()
    if error:
        return {"error": error}

    model = getattr(settings, "OPENAI_VIDEO_MODEL", "sora-2")
    seconds = _normalize_seconds(seconds)
    if size not in {"720x1280", "1280x720", "1024x1792", "1792x1024"}:
        size = "1280x720"

    data = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "seconds": str(seconds),
    }
    files = None
    if image_b64:
        try:
            image_bytes = base64.b64decode(image_b64)
            files = {"input_reference": ("reference.png", image_bytes, "image/png")}
        except Exception as exc:
            logger.warning("OpenAI video reference image ignored: %s", exc)

    try:
        response = requests.post(
            f"{OPENAI_VIDEO_API_BASE}/videos",
            headers=headers,
            data=data,
            files=files,
            timeout=60,
        )
        if response.status_code >= 400:
            return {"error": _response_error(response, "Erreur OpenAI Video API.")}
        payload = response.json()
        video_id = payload.get("id")
        if not video_id:
            return {"error": "OpenAI n'a pas retourné d'identifiant de vidéo."}
        return {"operation_name": f"openai:{video_id}", "provider": "openai", "error": None}
    except Exception as exc:
        logger.exception("Error starting OpenAI video generation")
        return {"error": str(exc)}


def check_openai_video_status(operation_name: str) -> dict:
    """Poll an OpenAI Sora video job and save the final MP4 locally."""
    headers, error = _headers()
    if error:
        return {"error": error}

    video_id = operation_name.removeprefix("openai:")
    try:
        response = requests.get(f"{OPENAI_VIDEO_API_BASE}/videos/{video_id}", headers=headers, timeout=30)
        if response.status_code >= 400:
            return {"error": _response_error(response, "Erreur lors du suivi OpenAI Video.")}
        payload = response.json()

        status = payload.get("status")
        if status in {"queued", "in_progress"}:
            return {"done": False, "progress": payload.get("progress", 0)}
        if status == "failed":
            err = payload.get("error") or {}
            return {"error": err.get("message", "La génération vidéo OpenAI a échoué.")}
        if status != "completed":
            return {"done": False, "progress": payload.get("progress", 0)}

        content_response = requests.get(
            f"{OPENAI_VIDEO_API_BASE}/videos/{video_id}/content",
            headers=headers,
            timeout=180,
        )
        content_response.raise_for_status()

        media_dir = os.path.join(settings.MEDIA_ROOT, "ai_videos")
        os.makedirs(media_dir, exist_ok=True)
        filename = f"openai_{uuid.uuid4().hex}.mp4"
        filepath = os.path.join(media_dir, filename)
        with open(filepath, "wb") as video_file:
            video_file.write(content_response.content)
        try:
            os.chmod(filepath, 0o644)
        except Exception:
            pass

        local_url = f"{settings.MEDIA_URL}ai_videos/{filename}"
        return {
            "done": True,
            "video_url": local_url,
            "local_path": f"ai_videos/{filename}",
            "error": None,
        }
    except Exception as exc:
        logger.exception("Error checking OpenAI video status")
        return {"error": str(exc)}
