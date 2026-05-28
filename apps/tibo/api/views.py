from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.tibo.api.serializers import CartSerializer, CategorySerializer, OrderSerializer, ProductSerializer, WishlistSerializer
from apps.tibo.models import Category, Order, Product, Wishlist
from apps.tibo.repositories import get_or_create_cart
from apps.tibo.selectors import product_list
from apps.tibo.services.cart_service import CartService


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return product_list(query=self.request.query_params.get("q"), category_slug=self.request.query_params.get("category"))


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = "slug"
    queryset = Category.objects.published()


class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        return Response(CartSerializer(get_or_create_cart(request)).data)

    @action(detail=False, methods=["post"])
    def add(self, request):
        cart = CartService.add(
            request,
            request.data.get("product_id"),
            request.data.get("quantity", 1),
            request.data.get("variant_id"),
        )
        return Response(CartSerializer(cart).data)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class WishlistViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related("product").prefetch_related("product__images")

