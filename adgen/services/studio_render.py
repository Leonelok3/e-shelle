"""Recoverable local render jobs; no external video API is called here."""
import logging
import threading
from django.db import close_old_connections, transaction
from django.utils import timezone
from adgen.models import StudioUsage, AdContent
from .studio_usage import finish

logger = logging.getLogger(__name__)


def run_render(pk):
    close_old_connections()
    try:
        if not StudioUsage.objects.filter(pk=pk, resource="video", status="reserved").update(status="running"):
            return
        job = StudioUsage.objects.select_related("campaign", "user").get(pk=pk)
        try:
            from .video_composer import VideoComposer
            from adgen.models import AdCinemaClip
            if not job.campaign or job.campaign.user_id != job.user_id:
                raise ValueError("Campagne indisponible.")
            offer = None
            if job.campaign.offer_id:
                from .studio_offers import source_for
                offer = source_for(job.campaign)
                if not offer or offer.price != job.campaign.prix:
                    raise ValueError("L’offre ou son tarif a changé avant le rendu.")
            cinema_id = job.payload.get("cinema_id")
            clip = AdCinemaClip.objects.get(pk=cinema_id, campaign=job.campaign, state="approved") if cinema_id else None
            composer = VideoComposer(job.campaign, duration=15,
                                     music_style=job.payload.get("music_style", "piano"),
                                     bg_config=job.payload.get("bg_config", {}),
                                     studio_media=job.payload.get("studio_media", {}),
                                     storyboard=job.payload.get("storyboard", {}), cinema=clip.video if clip else None,
                                     brand_logo=offer.business.logo if offer else None)
            url = composer.compose_from_photos()
            job.payload = {**job.payload, "video_url": url, "finished_at": timezone.now().isoformat()}
            if composer.rendered_captions:
                job.payload["storyboard"] = {**job.payload.get("storyboard", {}), "captions": composer.rendered_captions}
            if composer.caption_warning:
                job.payload["caption_warning"] = composer.caption_warning
            with transaction.atomic():
                if StudioUsage.objects.filter(pk=pk, status="running").update(payload=job.payload):
                    AdContent.objects.filter(campaign=job.campaign).update(ad_video_url=url)
                    finish(job)
        except Exception:
            logger.exception("AdGen Studio render failed: %s", pk)
            job.payload = {**job.payload, "error": "Le montage a échoué. Votre quota a été restitué ; vérifiez les photos et la durée de la voix-off (15 s maximum)."}
            with transaction.atomic():
                if StudioUsage.objects.filter(pk=pk, status="running").update(payload=job.payload):
                    finish(job, release=True)
    finally:
        close_old_connections()


def start_render(pk):
    # The DB reservation remains recoverable by the management command if the process stops.
    threading.Thread(target=run_render, args=(pk,), daemon=True).start()
