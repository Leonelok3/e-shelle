from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from business.models import BusinessProfile


class Command(BaseCommand):
    help = "Retrograde vers le plan Gratuit les fiches business dont l'abonnement est expire."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()
        candidates = BusinessProfile.objects.filter(
            Q(plan=BusinessProfile.Plan.FREE, free_visibility_expires_at__lte=now)
            | (
                ~Q(plan=BusinessProfile.Plan.FREE)
                & (
                    Q(subscription_expires_at__isnull=True)
                    | Q(subscription_expires_at__lte=now)
                )
            )
        )
        downgraded = 0
        checked = 0

        for business in candidates.iterator(chunk_size=100):
            checked += 1
            was_free = business.plan == BusinessProfile.Plan.FREE
            if dry_run:
                action = "mettre en pause" if was_free else "retrograder -> Gratuit"
                self.stdout.write(f"{business.pk} {business.name}: {action}")
                continue
            if business.check_expiry():
                downgraded += 1
                action = "mise en pause" if was_free else "retrograde -> Gratuit"
                self.stdout.write(f"{business.pk} {business.name}: {action}")

        self.stdout.write(
            f"Termine. {checked} fiche(s) expiree(s) verifiee(s), {downgraded} traitee(s)."
        )
