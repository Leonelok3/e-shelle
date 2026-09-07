from django.core.management.base import BaseCommand
from django.utils import timezone

from business.models import BusinessProfile


class Command(BaseCommand):
    help = "Retrograde vers le plan Gratuit les fiches business dont l'abonnement est expire."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        candidates = BusinessProfile.objects.exclude(plan=BusinessProfile.Plan.FREE)
        downgraded = 0
        checked = 0

        for business in candidates.iterator(chunk_size=100):
            checked += 1
            is_expired = (
                business.subscription_expires_at
                and timezone.now() > business.subscription_expires_at
            )
            if not is_expired:
                continue
            if dry_run:
                self.stdout.write(f"{business.pk} {business.name}: retrograderait -> Gratuit")
                continue
            if business.check_expiry():
                downgraded += 1
                self.stdout.write(f"{business.pk} {business.name}: retrograde -> Gratuit")

        self.stdout.write(
            f"Termine. {checked} fiche(s) payante(s) verifiee(s), {downgraded} retrogradee(s)."
        )
