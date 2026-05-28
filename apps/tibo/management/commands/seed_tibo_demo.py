from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.tibo.models import Brand, Category, Inventory, Product, ProductImage, ProductTag, Supplier


class Command(BaseCommand):
    help = "Ajoute des produits de démonstration premium pour la boutique TIBO."

    def handle(self, *args, **options):
        supplier_shopify, _ = Supplier.objects.get_or_create(
            name="TIBO Shopify Partner",
            defaults={
                "source": Supplier.SOURCE_SHOPIFY,
                "website": "https://shopify.com",
                "commission_rate": Decimal("12.00"),
                "is_active": True,
            },
        )
        supplier_amazon, _ = Supplier.objects.get_or_create(
            name="Amazon Canada Affiliate",
            defaults={
                "source": Supplier.SOURCE_AMAZON,
                "website": "https://www.amazon.ca",
                "affiliate_tag": "tibo-20",
                "commission_rate": Decimal("8.00"),
                "is_active": True,
            },
        )

        categories = {
            "Maison connectée": Category.objects.get_or_create(
                name="Maison connectée",
                defaults={
                    "description": "Objets intelligents et élégants pour un intérieur moderne.",
                    "accent_color": "#69e7ff",
                    "is_featured": True,
                    "sort_order": 1,
                },
            )[0],
            "Bureau premium": Category.objects.get_or_create(
                name="Bureau premium",
                defaults={
                    "description": "Accessoires de productivité pour espace de travail haut de gamme.",
                    "accent_color": "#2f7cff",
                    "is_featured": True,
                    "sort_order": 2,
                },
            )[0],
            "Voyage Canada": Category.objects.get_or_create(
                name="Voyage Canada",
                defaults={
                    "description": "Essentiels compacts pour déplacements, hiver et quotidien.",
                    "accent_color": "#ffffff",
                    "is_featured": True,
                    "sort_order": 3,
                },
            )[0],
        }

        brands = {
            "Northline": Brand.objects.get_or_create(name="Northline", defaults={"is_featured": True})[0],
            "AeroHaus": Brand.objects.get_or_create(name="AeroHaus", defaults={"is_featured": True})[0],
            "Volt & Vale": Brand.objects.get_or_create(name="Volt & Vale", defaults={"is_featured": True})[0],
        }

        tags = {}
        for tag_name in ["premium", "canada", "tendance", "cadeau", "smart"]:
            tags[tag_name] = ProductTag.objects.get_or_create(name=tag_name)[0]

        products = [
            {
                "title": "Lampe AuraDesk Pro",
                "sku": "TIBO-AURA-001",
                "source": Product.SOURCE_SHOPIFY,
                "external_id": "demo-shopify-aura-001",
                "supplier": supplier_shopify,
                "brand": brands["AeroHaus"],
                "category": categories["Bureau premium"],
                "short_description": "Lampe LED intelligente avec charge sans fil, variation chaude/froide et présence ultra minimaliste.",
                "description": "La Lampe AuraDesk Pro transforme un bureau en espace calme et productif avec une lumière réglable, un socle stable et une zone de charge compatible appareils modernes.",
                "price": Decimal("129.00"),
                "compare_at_price": Decimal("169.00"),
                "cost_price": Decimal("78.00"),
                "currency": "CAD",
                "commission_rate": Decimal("12.00"),
                "is_featured": True,
                "is_trending": True,
                "image": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "title": "Station MagDock Titanium",
                "sku": "TIBO-MAG-002",
                "source": Product.SOURCE_AMAZON,
                "external_id": "B0DEMO002",
                "supplier": supplier_amazon,
                "brand": brands["Volt & Vale"],
                "category": categories["Bureau premium"],
                "short_description": "Station 3-en-1 magnétique pour téléphone, écouteurs et montre, pensée pour les setups propres.",
                "description": "MagDock Titanium centralise la recharge quotidienne dans un bloc dense, stable et discret. Idéal pour bureaux, tables de nuit et espaces minimalistes.",
                "price": Decimal("89.95"),
                "compare_at_price": Decimal("119.95"),
                "cost_price": Decimal("51.00"),
                "currency": "CAD",
                "commission_rate": Decimal("8.00"),
                "is_featured": True,
                "is_trending": True,
                "affiliate_url": "https://www.amazon.ca/dp/B0DEMO002?tag=tibo-20",
                "image": "https://images.unsplash.com/photo-1618577608401-17f89a4ecfa4?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "title": "Diffuseur SmartMist Noir Mat",
                "sku": "TIBO-MIST-003",
                "source": Product.SOURCE_SHOPIFY,
                "external_id": "demo-shopify-mist-003",
                "supplier": supplier_shopify,
                "brand": brands["Northline"],
                "category": categories["Maison connectée"],
                "short_description": "Diffuseur compact connecté avec ambiance lumineuse douce et arrêt automatique.",
                "description": "SmartMist apporte une atmosphère calme à la maison avec une finition noire mate, un éclairage subtil et une gestion simple du cycle de diffusion.",
                "price": Decimal("74.00"),
                "compare_at_price": Decimal("99.00"),
                "cost_price": Decimal("42.00"),
                "currency": "CAD",
                "commission_rate": Decimal("13.00"),
                "is_featured": True,
                "is_trending": False,
                "image": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "title": "Sac Weekender Glacier",
                "sku": "TIBO-GLACIER-004",
                "source": Product.SOURCE_AMAZON,
                "external_id": "B0DEMO004",
                "supplier": supplier_amazon,
                "brand": brands["Northline"],
                "category": categories["Voyage Canada"],
                "short_description": "Sac de voyage élégant, résistant à l’eau, compartiment laptop et poche chaussures.",
                "description": "Pensé pour les fins de semaine canadiennes, Glacier offre une structure légère, des poches intelligentes et un look sobre qui passe du bureau à l’aéroport.",
                "price": Decimal("149.00"),
                "compare_at_price": Decimal("189.00"),
                "cost_price": Decimal("88.00"),
                "currency": "CAD",
                "commission_rate": Decimal("9.00"),
                "is_featured": True,
                "is_trending": True,
                "affiliate_url": "https://www.amazon.ca/dp/B0DEMO004?tag=tibo-20",
                "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "title": "ThermoCup North 720",
                "sku": "TIBO-CUP-005",
                "source": Product.SOURCE_SHOPIFY,
                "external_id": "demo-shopify-cup-005",
                "supplier": supplier_shopify,
                "brand": brands["Volt & Vale"],
                "category": categories["Voyage Canada"],
                "short_description": "Gobelet isotherme premium 720 ml, fini graphite, idéal hiver canadien.",
                "description": "ThermoCup North conserve boissons chaudes ou froides avec une prise en main agréable, un couvercle étanche et une silhouette premium.",
                "price": Decimal("39.95"),
                "compare_at_price": Decimal("54.95"),
                "cost_price": Decimal("19.00"),
                "currency": "CAD",
                "commission_rate": Decimal("15.00"),
                "is_featured": False,
                "is_trending": True,
                "image": "https://images.unsplash.com/photo-1577937927133-66ef06acdf18?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "title": "Caméra DoorView Mini",
                "sku": "TIBO-DOOR-006",
                "source": Product.SOURCE_AMAZON,
                "external_id": "B0DEMO006",
                "supplier": supplier_amazon,
                "brand": brands["AeroHaus"],
                "category": categories["Maison connectée"],
                "short_description": "Caméra de porte compacte avec vision nocturne, alertes mobiles et installation simple.",
                "description": "DoorView Mini sécurise l’entrée avec un format discret, des notifications rapides et une intégration facile dans une maison connectée.",
                "price": Decimal("119.95"),
                "compare_at_price": Decimal("159.95"),
                "cost_price": Decimal("71.00"),
                "currency": "CAD",
                "commission_rate": Decimal("8.00"),
                "is_featured": True,
                "is_trending": True,
                "affiliate_url": "https://www.amazon.ca/dp/B0DEMO006?tag=tibo-20",
                "image": "https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=1200&q=80",
            },
        ]

        created_or_updated = 0
        for item in products:
            image_url = item.pop("image")
            product, _ = Product.all_objects.update_or_create(
                sku=item["sku"],
                defaults={**item, "is_active": True},
            )
            product.tags.set([tags["premium"], tags["canada"], tags["tendance"]])
            Inventory.objects.update_or_create(
                product=product,
                defaults={"quantity": 24, "reserved": 0, "low_stock_threshold": 5, "sync_enabled": True},
            )
            ProductImage.objects.update_or_create(
                product=product,
                is_primary=True,
                defaults={"remote_url": image_url, "alt_text": product.title, "sort_order": 0},
            )
            created_or_updated += 1

        self.stdout.write(self.style.SUCCESS(f"{created_or_updated} produits de test TIBO prêts."))
