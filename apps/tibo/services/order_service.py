from django.db import transaction

from apps.tibo.models import Order, OrderItem


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_from_cart(cart, email, shipping_address=None, billing_address=None, user=None):
        order = Order.objects.create(
            user=user,
            email=email,
            currency=cart.currency,
            subtotal=cart.subtotal,
            discount_total=cart.discount_total,
            tax_total=cart.tax_total,
            shipping_total=cart.shipping_total,
            total=cart.total,
            shipping_address=shipping_address or {},
            billing_address=billing_address or shipping_address or {},
        )
        for item in cart.items.select_related("product", "variant", "product__supplier"):
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                title=item.product.title,
                supplier_source=item.product.source,
                external_product_id=item.product.external_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )
        cart.items.all().delete()
        cart.coupon = None
        cart.save(update_fields=["coupon", "updated_at"])
        return order

