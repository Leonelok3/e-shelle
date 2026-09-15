import logging
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.files import File
from django.utils import timezone

from .models import OCRJob
from .services import OCRError, extract_from_image, extract_from_video

logger = logging.getLogger(__name__)


def upload_root():
    return Path(getattr(settings, "PHONE_OCR_UPLOAD_ROOT", settings.BASE_DIR / "var" / "phone_ocr"))


def cleanup_files(job):
    root = upload_root().resolve()
    for item in job.files:
        path = (root / item["name"]).resolve()
        if path.parent == root:
            path.unlink(missing_ok=True)


@shared_task(ignore_result=True, soft_time_limit=3500, time_limit=3600)
def process_ocr_job(job_id):
    if not OCRJob.objects.filter(pk=job_id, status="queued").update(status="running", updated_at=timezone.now()):
        return
    job = OCRJob.objects.get(pk=job_id)
    try:
        numbers, texts = [], []
        for item in job.files:
            with (upload_root() / item["name"]).open("rb") as stream:
                media = File(stream, name=item["name"])
                extract = extract_from_video if item["type"].startswith("video/") else extract_from_image
                result = extract(media)
                numbers.extend(result.whatsapp_numbers)
                texts.append(result.text)
        OCRJob.objects.filter(pk=job_id, status="running").update(
            status="done", numbers=list(dict.fromkeys(numbers)), text="\n---\n".join(texts), updated_at=timezone.now())
    except Exception as exc:
        logger.exception("OCR job failed: %s", job_id)
        OCRJob.objects.filter(pk=job_id).update(status="failed", error=str(exc) if isinstance(exc, OCRError) else "Analyse interrompue ou impossible. Réessayez avec un extrait plus court.", updated_at=timezone.now())
    finally:
        cleanup_files(job)


@shared_task(ignore_result=True)
def cleanup_ocr_jobs():
    now = timezone.now()
    for job in OCRJob.objects.filter(status__in=["queued", "running"], updated_at__lt=now - timedelta(hours=2)):
        OCRJob.objects.filter(pk=job.pk, status__in=["queued", "running"]).update(status="failed", error="Le délai de traitement a été dépassé. Veuillez réessayer.", updated_at=now)
        cleanup_files(job)
    for job in OCRJob.objects.filter(created_at__lt=now - timedelta(days=1)).exclude(status__in=["queued", "running"]):
        cleanup_files(job)
        job.delete()
