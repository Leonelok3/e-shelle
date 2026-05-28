import os

import requests

from apps.tibo.services.product_service import ProductService


class ShopifyService:
    def __init__(self, shop_domain=None, access_token=None):
        self.shop_domain = shop_domain or os.getenv("TIBO_SHOPIFY_SHOP_DOMAIN", "")
        self.access_token = access_token or os.getenv("TIBO_SHOPIFY_ACCESS_TOKEN", "")
        self.api_version = os.getenv("TIBO_SHOPIFY_API_VERSION", "2026-01")

    @property
    def base_url(self):
        return f"https://{self.shop_domain}/admin/api/{self.api_version}"

    def _headers(self):
        return {"X-Shopify-Access-Token": self.access_token, "Content-Type": "application/json"}

    def import_products(self, limit=50):
        if not self.shop_domain or not self.access_token:
            return []
        response = requests.get(f"{self.base_url}/products.json", headers=self._headers(), params={"limit": limit}, timeout=30)
        response.raise_for_status()
        imported = []
        for item in response.json().get("products", []):
            variant = (item.get("variants") or [{}])[0]
            payload = {
                "external_id": item["id"],
                "title": item["title"],
                "short_description": item.get("body_html", "")[:300],
                "description": item.get("body_html", ""),
                "category": item.get("product_type") or "Shopify",
                "price": variant.get("price") or "0.00",
                "compare_at_price": variant.get("compare_at_price"),
                "currency": "CAD",
                "quantity": variant.get("inventory_quantity") or 0,
                "canonical_url": f"https://{self.shop_domain}/products/{item.get('handle')}",
                "images": [image.get("src") for image in item.get("images", []) if image.get("src")],
                "metadata": item,
            }
            imported.append(ProductService.upsert_external_product("shopify", payload))
        return imported

    def sync_inventory(self):
        return self.import_products()

    def sync_orders(self):
        return []

    def update_prices(self):
        return self.import_products()

