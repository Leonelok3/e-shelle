import hashlib
import hmac
import os
from urllib.parse import urlencode

from apps.tibo.services.product_service import ProductService


class AmazonService:
    def __init__(self):
        self.access_key = os.getenv("TIBO_AMAZON_ACCESS_KEY", "")
        self.secret_key = os.getenv("TIBO_AMAZON_SECRET_KEY", "")
        self.partner_tag = os.getenv("TIBO_AMAZON_PARTNER_TAG", "")
        self.marketplace = os.getenv("TIBO_AMAZON_MARKETPLACE", "www.amazon.ca")

    def search_products(self, keywords, limit=10):
        if not self.access_key or not self.secret_key:
            return []
        return []

    def import_product(self, payload):
        payload.setdefault("affiliate_url", self.generate_affiliate_link(payload.get("asin", payload["external_id"])))
        return ProductService.upsert_external_product("amazon", payload)

    def sync_prices(self):
        return []

    def generate_affiliate_link(self, asin):
        params = {"tag": self.partner_tag, "linkCode": "ogi", "th": "1", "psc": "1"}
        return f"https://{self.marketplace}/dp/{asin}?{urlencode(params)}"

    def sign_debug_token(self, value):
        return hmac.new(self.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()
