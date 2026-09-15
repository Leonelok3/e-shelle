import logging
import uuid
from pathlib import Path

from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import OCRJob
from .tasks import cleanup_files, process_ocr_job, upload_root

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "video/mp4", "video/quicktime",
    "video/x-matroska", "video/webm", "video/avi", "video/x-msvideo",
}


def owned_job(request, job_id):
    try:
        job_id = uuid.UUID(str(job_id))
    except ValueError:
        raise Http404
    return get_object_or_404(OCRJob, pk=job_id, session_key=request.session.session_key or "")


@require_POST
def submit(request):
    files = request.FILES.getlist("media")
    if not files:
        return JsonResponse({"error": "Sélectionnez au moins une image ou vidéo."}, status=400)
    if sum(f.size for f in files) > MAX_UPLOAD_BYTES:
        return JsonResponse({"error": "La taille totale dépasse 200 Mo. Réduisez la sélection ou compressez les vidéos."}, status=413)
    if any(f.content_type not in ALLOWED_CONTENT_TYPES for f in files):
        return JsonResponse({"error": "Format refusé. Utilisez PNG, JPG, MP4, MOV, WEBM, MKV ou AVI."}, status=400)
    if not request.session.session_key:
        request.session.create()
    root = upload_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    job = OCRJob(session_key=request.session.session_key)
    try:
        for media in files:
            name = uuid.uuid4().hex + Path(media.name).suffix.lower()
            job.files.append({"name": name, "type": media.content_type})
            with (root / name).open("xb") as stream:
                for chunk in media.chunks():
                    stream.write(chunk)
        job.save()
        process_ocr_job.apply_async(args=[str(job.pk)], retry=False)
    except Exception:
        logging.getLogger(__name__).exception("Unable to queue OCR")
        cleanup_files(job)
        if not job._state.adding:
            job.status, job.error = "failed", "Le service d’analyse est indisponible. Réessayez plus tard."
            job.save(update_fields=["status", "error", "updated_at"])
        return JsonResponse({"error": "Le service d’analyse est indisponible. Réessayez plus tard."}, status=503)
    result_url = reverse("phone_ocr_agent:dashboard") + "?job=" + str(job.pk)
    if request.headers.get("Accept") != "application/json":
        return redirect(result_url)
    return JsonResponse({"status_url": reverse("phone_ocr_agent:job_status", args=[job.pk]), "result_url": result_url}, status=202)


def status(request, job_id):
    job = owned_job(request, job_id)
    response = JsonResponse({"status": job.status, "error": job.error})
    response["Cache-Control"] = "no-store"
    return response
