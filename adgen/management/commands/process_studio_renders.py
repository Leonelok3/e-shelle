from django.core.management.base import BaseCommand
from adgen.models import StudioUsage
from adgen.services.studio_render import run_render
from datetime import timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = "Traite les montages Studio en attente. À exécuter périodiquement pour reprendre la file persistante."

    def handle(self, *args, **options):
        # No automatic paid retries. Rendering has a bounded 300 s subprocess.
        stale = StudioUsage.objects.filter(status__in=["reserved", "running"], created_at__lt=timezone.now() - timedelta(hours=2))
        stale.filter(resource__in=["voice", "text"]).update(status="failed")
        stale.filter(resource__in=["video", "music"]).update(status="released", payload={"error": "Le traitement a été interrompu. Quota restitué ; vous pouvez relancer."})
        for pk in StudioUsage.objects.filter(resource="video", status="reserved").values_list("pk", flat=True):
            run_render(pk)
