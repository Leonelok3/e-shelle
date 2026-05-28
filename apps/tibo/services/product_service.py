from decimal import Decimal

from django.db import transaction

from apps.tibo.models import Category, Inventory, Product, ProductImage, Supplier


class ProductService:
    @staticmethod
    @transaction.atomic
    def upsert_external_product(source, payload, supplier=None):
        category_name = payload.get("category") or "Sélection TIBO"
        category, _ = Category.objects.get_or_create(name=category_name, defaults={"slug": ""})
        supplier_obj = supplier
        if supplier_obj is None:
            supplier_obj, _ = Supplier.objects.get_or_create(
                name=payload.get("supplier_name") or source.title(),
                source=source,
            )
        product, _ = Product.all_objects.update_or_create(
            source=source,
            external_id=str(payload["external_id"]),
            defaults={
                "title": payload["title"],
                "short_description": payload.get("short_description", "")[:320],
                "description": payload.get("description") or payload.get("short_description") or payload["title"],
                "category": category,
                "supplier": supplier_obj,
                "price": Decimal(str(payload.get("price", "0.00"))),
                "compare_at_price": payload.get("compare_at_price"),
                "currency": payload.get("currency", "CAD"),
                "affiliate_url": payload.get("affiliate_url", ""),
                "canonical_url": payload.get("canonical_url", ""),
                "is_active": payload.get("is_active", True),
                "metadata": payload.get("metadata", {}),
            },
        )
        Inventory.objects.get_or_create(product=product, defaults={"quantity": int(payload.get("quantity", 0))})
        for index, image_url in enumerate(payload.get("images", [])):
            ProductImage.objects.get_or_create(
                product=product,
                remote_url=image_url,
                defaults={"is_primary": index == 0, "sort_order": index, "alt_text": product.title},
            )
        return product

