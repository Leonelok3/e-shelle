from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.tibo.models import CartItem, Coupon, Product, ProductVariant
from apps.tibo.repositories import get_or_create_cart


class CartService:
    @staticmethod
    @transaction.atomic
    def add(request, product_id, quantity=1, variant_id=None):
        cart = get_or_create_cart(request)
        product = get_object_or_404(Product.objects.published(), id=product_id)
        variant = None
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={"quantity": max(int(quantity), 1)},
        )
        if not created:
            item.quantity += max(int(quantity), 1)
            item.save(update_fields=["quantity", "updated_at"])
        return cart

    @staticmethod
    @transaction.atomic
    def update_item(cart, item_id, quantity):
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        quantity = max(int(quantity), 0)
        if quantity == 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save(update_fields=["quantity", "updated_at"])
        return cart

    @staticmethod
    def apply_coupon(cart, code):
        coupon = Coupon.objects.filter(code__iexact=code.strip(), is_active=True).first()
        if coupon and coupon.is_valid():
            cart.coupon = coupon
            cart.save(update_fields=["coupon", "updated_at"])
            return True
        return False

