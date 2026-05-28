from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tibo.models import Cart


class Command(BaseCommand):
    help = "Nettoie les paniers TIBO anciens et vides."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        count, _ = Cart.objects.filter(updated_at__lt=cutoff, items__isnull=True).delete()
        self.stdout.write(self.style.SUCCESS(f"{count} objets supprimés."))

