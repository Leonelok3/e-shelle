# mediafiles/views.py
from pathlib import Path
import mimetypes

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)


def _safe_abs_path(rel_path: str) -> Path:
    requested = Path(rel_path)

    # Anti path traversal
    if ".." in requested.parts:
        raise PermissionError("Invalid path.")

    abs_path = (Path(settings.PROTECTED_MEDIA_ROOT) / requested).resolve()
    root_path = Path(settings.PROTECTED_MEDIA_ROOT).resolve()

    # Garantit que le fichier reste dans PROTECTED_MEDIA_ROOT
    if not str(abs_path).startswith(str(root_path)):
        raise PermissionError("Invalid path.")

    return abs_path


@login_required
def protected_media_probe(request, path: str):
    """
    Endpoint diagnostic (utile en local uniquement).
    En production tu peux le laisser, il est protégé par login.
    """
    try:
        abs_path = _safe_abs_path(path)
    except PermissionError:
        return JsonResponse({"ok": False, "error": "invalid_path"}, status=403)

    exists = abs_path.exists() and abs_path.is_file()
    content_type, _ = mimetypes.guess_type(str(abs_path))

    return JsonResponse(
        {
            "ok": True,
            "exists": exists,
            "abs_path": str(abs_path),
            "size": abs_path.stat().st_size if exists else None,
            "content_type": content_type or "application/octet-stream",
            "debug": settings.DEBUG,
            "protected_media_root": str(settings.PROTECTED_MEDIA_ROOT),
            "requested": path,
        }
    )


@login_required
def protected_media(request, path: str):
    """
    Protected media streaming.

    DEV (DEBUG=True):
      - Django sert le fichier
      - support HTTP Range (audio/vidéo)

    PROD (DEBUG=False):
      - délégation Nginx via X-Accel-Redirect (range + perf natifs)
    """
    try:
        abs_path = _safe_abs_path(path)
    except PermissionError:
        return HttpResponseForbidden("Invalid path.")

    if not abs_path.exists() or not abs_path.is_file():
        raise Http404("File not found.")

    # =========================
    # PROD -> Nginx sert le fichier
    # =========================
    if not settings.DEBUG:
        response = HttpResponse()
        response["Content-Type"] = ""  # Nginx déterminera
        response["X-Accel-Redirect"] = f"/_protected_media/{Path(path).as_posix()}"
        response["Cache-Control"] = "private, max-age=86400"
        return response

    # =========================
    # DEV -> Django sert avec Range
    # =========================
    file_size = abs_path.stat().st_size
    content_type, _ = mimetypes.guess_type(str(abs_path))
    content_type = content_type or "application/octet-stream"

    range_header = request.headers.get("Range")
    if range_header:
        try:
            units, rng = range_header.split("=", 1)
            if units.strip().lower() != "bytes":
                return HttpResponse(status=416)

            start_str, end_str = (rng.split("-", 1) + [""])[:2]
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1

            if start < 0 or end < start:
                return HttpResponse(status=416)

            end = min(end, file_size - 1)
            length = end - start + 1

            with open(abs_path, "rb") as f:
                f.seek(start)
                data = f.read(length)

            resp = HttpResponse(data, status=206, content_type=content_type)
            resp["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            resp["Accept-Ranges"] = "bytes"
            resp["Content-Length"] = str(length)
            resp["Cache-Control"] = "private, max-age=0"
            return resp
        except Exception:
            return HttpResponse(status=416)

    resp = FileResponse(open(abs_path, "rb"), content_type=content_type)
    resp["Accept-Ranges"] = "bytes"
    resp["Content-Length"] = str(file_size)
    resp["Cache-Control"] = "private, max-age=0"
    return resp
