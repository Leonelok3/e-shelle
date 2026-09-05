from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.canada_validation import check_offer, parse_deadline
from jobs.models import CanadaJobOffer


class Command(BaseCommand):
    help = "Supprime les offres Canada expirées avec preuve; masque les sources non vérifiables."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        counts = {"expired": 0, "active": 0, "unknown": 0}
        today = timezone.localdate()
        for offer in CanadaJobOffer.objects.all().iterator(chunk_size=100):
            deadline = parse_deadline(offer.deadline)
            if deadline and deadline < today:
                status, reason, source_deadline = "expired", "Date limite dépassée", None
            else:
                status, reason, source_deadline = check_offer(offer.url_apply)
                if source_deadline and source_deadline < today:
                    status, reason = "expired", "Date limite source dépassée"
            counts[status] += 1
            self.stdout.write(f"{offer.pk}: {status} - {reason}")
            if options["dry_run"]:
                continue
            # Do not touch a row updated by the importer during the network check.
            current = CanadaJobOffer.objects.filter(pk=offer.pk, last_seen=offer.last_seen)
            if status == "expired":
                current.delete()
            else:
                values = {"is_active": status == "active"}
                if source_deadline:
                    values["deadline"] = source_deadline.isoformat()
                current.update(**values)
        self.stdout.write(f"Simulation={options['dry_run']} Résultat: {counts}")
