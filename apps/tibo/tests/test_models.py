from django.test import TestCase

from apps.tibo.models import Category, Product


class ProductModelTests(TestCase):
    def test_product_slug_is_generated(self):
        category = Category.objects.create(name="Maison premium")
        product = Product.objects.create(
            title="Lampe intelligente TIBO",
            category=category,
            description="Produit premium pour maison connectée.",
            price="79.00",
        )
        self.assertEqual(product.slug, "lampe-intelligente-tibo")
