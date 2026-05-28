from django.core.management.base import BaseCommand

from apps.tibo.services.shopify_service import ShopifyService


class Command(BaseCommand):
    help = "Importe les produits TIBO depuis Shopify."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        imported = ShopifyService().import_products(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"{len(imported)} produits importés."))

