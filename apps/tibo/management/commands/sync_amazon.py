from django.core.management.base import BaseCommand

from apps.tibo.services.amazon_service import AmazonService


class Command(BaseCommand):
    help = "Synchronise les prix Amazon Product Advertising API pour TIBO."

    def handle(self, *args, **options):
        products = AmazonService().sync_prices()
        self.stdout.write(self.style.SUCCESS(f"Amazon synchronisé: {len(products)} produits."))

