from celery import shared_task
from .models import Source
from .services.ingestion import run_source

@shared_task(name="radar.refresh_all")
def refresh_all():
    total = 0
    for src in Source.objects.filter(active=True):
        total += run_source(src)
    return total

@shared_task(name="radar.refresh_one")
def refresh_one(source_id: int):
    src = Source.objects.get(id=source_id)
    return run_source(src)
