from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from business.catalog_import import MAX_CSV_BYTES, CatalogImportError, import_catalog_csv
from business.models import BusinessProfile


class Command(BaseCommand):
    help = "Importe ou met à jour un catalogue grossiste CSV pour Tchokos Sarl."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument(
            "--business-id",
            type=int,
            help="Identifiant du profil Business cible. Par défaut, recherche Tchokos Sarl.",
        )

    def handle(self, *args, **options):
        if options["business_id"]:
            business = BusinessProfile.objects.filter(pk=options["business_id"]).first()
            if business is None:
                raise CommandError("Aucun profil Business ne correspond à --business-id.")
        else:
            matches = BusinessProfile.objects.filter(name__iexact="Tchokos Sarl")
            if matches.count() != 1:
                raise CommandError(
                    "Tchokos Sarl doit désigner un seul profil. Précise --business-id."
                )
            business = matches.first()

        csv_path = options["csv_path"]
        try:
            if csv_path.stat().st_size > MAX_CSV_BYTES:
                raise CommandError("Le fichier CSV dépasse la limite de 5 Mo.")
            with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                result = import_catalog_csv(business, csv_file)
        except CommandError:
            raise
        except OSError as exc:
            raise CommandError(f"Impossible de lire le CSV {csv_path}: {exc}") from exc
        except CatalogImportError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"{result['created']} créé(s), {result['updated']} mis à jour, "
                f"{result['total']} ligne(s) traitée(s) pour {business.name}."
            )
        )
