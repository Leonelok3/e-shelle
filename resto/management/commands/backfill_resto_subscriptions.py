from datetime import date, timedelta

from django.core.management.base import BaseCommand

from resto.models import Restaurant, Subscription


class Command(BaseCommand):
    help = (
        "Cree un abonnement essai gratuit (30 jours) pour les restaurants "
        "qui n'en ont aucun (bug de creation manuelle/admin). Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--trial-days", type=int, default=30)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        trial_days = options["trial_days"]
        missing = Restaurant.objects.filter(subscription__isnull=True)
        count = missing.count()

        if count == 0:
            self.stdout.write("Aucun restaurant sans abonnement. Rien a faire.")
            return

        for restaurant in missing:
            self.stdout.write(f"{restaurant.pk} {restaurant.name} : abonnement manquant")
            if not dry_run:
                Subscription.objects.create(
                    restaurant=restaurant,
                    plan="free_trial",
                    expiry_date=date.today() + timedelta(days=trial_days),
                )

        if dry_run:
            self.stdout.write(f"Simulation : {count} abonnement(s) seraient crees.")
        else:
            self.stdout.write(self.style.SUCCESS(f"{count} abonnement(s) cree(s)."))
