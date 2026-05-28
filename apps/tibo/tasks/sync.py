from apps.tibo.services.amazon_service import AmazonService
from apps.tibo.services.shopify_service import ShopifyService
from apps.tibo.tasks import shared_task


@shared_task(name="tibo.sync_shopify_products")
def sync_shopify_products():
    return len(ShopifyService().import_products())


@shared_task(name="tibo.sync_amazon_prices")
def sync_amazon_prices():
    return len(AmazonService().sync_prices())


@shared_task(name="tibo.send_order_email")
def send_order_email(order_id):
    return {"order_id": str(order_id), "sent": False}


@shared_task(name="tibo.cleanup_old_carts")
def cleanup_old_carts():
    return 0

