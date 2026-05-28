from rest_framework import serializers

from apps.tibo.models import Cart, CartItem, Category, Order, OrderItem, Product, ProductImage, Wishlist


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.CharField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ["id", "url", "alt_text", "is_primary", "sort_order"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "accent_color", "is_featured"]


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    absolute_url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "sku",
            "source",
            "category",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "currency",
            "rating_average",
            "rating_count",
            "is_featured",
            "is_trending",
            "discount_percent",
            "absolute_url",
            "images",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "variant", "quantity", "unit_price", "line_total"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "currency", "items", "subtotal", "discount_total", "tax_total", "shipping_total", "total", "item_count"]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "title", "quantity", "unit_price", "line_total", "fulfillment_status", "tracking_url"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "number", "status", "currency", "subtotal", "tax_total", "shipping_total", "total", "items", "created_at"]


class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "product", "created_at"]

