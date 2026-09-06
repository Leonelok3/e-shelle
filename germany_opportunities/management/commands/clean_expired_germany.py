from django.core.management.base import BaseCommand
from germany_opportunities.availability import clean_unavailable


class Command(BaseCommand):
    help = "Masque les offres anciennes et les bourses expirées ou sans échéance vérifiable."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--check-links", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(f"Simulation={options['dry_run']}: {clean_unavailable(options['dry_run'])}")
        if options["check_links"]:
            from germany_opportunities.source_checks import check_sources
            self.stdout.write(str(check_sources(options["dry_run"])))
