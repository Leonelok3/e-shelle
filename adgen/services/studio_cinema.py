"""Optional staff pilot for a short, reviewable Runway insert."""

import base64
import io
import tempfile
import uuid
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.files import File
from PIL import Image, ImageOps

API = "https://api.dev.runwayml.com/v1"
MODEL = "gen4_turbo"
DURATION = 5
PROVIDER_COST_CREDITS = 25
MAX_OUTPUT = 25 * 1024 * 1024


def enabled():
    return bool(getattr(settings, "ADGEN_RUNWAY_API_KEY", ""))


def _headers():
    return {"Authorization": f"Bearer {settings.ADGEN_RUNWAY_API_KEY}", "X-Runway-Version": "2024-11-06"}


def _photo_payload(photo):
    with photo.open("rb") as source, Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((720, 1280))
        canvas = Image.new("RGB", (720, 1280), "#171717")
        canvas.paste(image, ((720 - image.width) // 2, (1280 - image.height) // 2))
        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def start_clip(clip, image):
    response = requests.post(f"{API}/image_to_video", headers=_headers(), allow_redirects=False, timeout=20, json={
        "model": MODEL, "duration": DURATION, "ratio": "720:1280", "promptImage": image,
        "promptText": "Slow, smooth commercial camera push toward the exact subject in the source photograph. Preserve its appearance, shape, colours, proportions and setting. No new objects, people, signs, labels, writing or added branding.",
    })
    if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
        raise ValueError("Runway a refusé la demande.")
    clip.task_id = uuid.UUID(response.json()["id"])
    clip.state = "pending"
    clip.save(update_fields=["task_id", "state"])


def _download(url, clip):
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443)
            or not host.endswith((".cloudfront.net", ".runwayml.cloud", ".runwayml.com"))):
        raise ValueError("Stockage Runway inconnu.")
    with requests.get(url, stream=True, allow_redirects=False, timeout=(5, 20)) as response, tempfile.TemporaryFile() as asset:
        if response.status_code != 200:
            raise ValueError("Le plan Runway n’est pas téléchargeable.")
        size = 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > MAX_OUTPUT:
                raise ValueError("Le plan Runway dépasse la taille autorisée.")
            asset.write(chunk)
        asset.seek(0)
        if asset.read(8)[4:8] != b"ftyp":
            raise ValueError("Runway n’a pas renvoyé de fichier MP4.")
        asset.seek(0)
        clip.video.save(f"{uuid.uuid4().hex}.mp4", File(asset), save=False)


def refresh_clip(clip):
    response = requests.get(f"{API}/tasks/{clip.task_id}", headers=_headers(), allow_redirects=False, timeout=15)
    if response.status_code != 200:
        raise ValueError("État du plan indisponible.")
    status = response.json()
    state = status.get("status")
    if state == "SUCCEEDED":
        _download(status["output"][0], clip)
        clip.state = "review"
        clip.save(update_fields=["video", "state"])
    if state in {"FAILED", "CANCELLED"}:
        clip.state = "failed"
        clip.save(update_fields=["state"])
