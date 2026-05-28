from django.core.management.base import BaseCommand

from apps.tibo.services.shopify_service import ShopifyService


class Command(BaseCommand):
    help = "Synchronise produits, prix et stock Shopify pour TIBO."

    def handle(self, *args, **options):
        products = ShopifyService().sync_inventory()
        self.stdout.write(self.style.SUCCESS(f"Shopify synchronisé: {len(products)} produits."))

