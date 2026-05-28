from django.contrib import admin
from django.utils.html import format_html

from apps.tibo.models import (
    Address,
    AffiliateProfile,
    Brand,
    Cart,
    CartItem,
    Category,
    Commission,
    Coupon,
    Inventory,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductImage,
    ProductReview,
    ProductTag,
    ProductVariant,
    Supplier,
    Wishlist,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["preview", "image", "remote_url", "alt_text", "is_primary", "sort_order"]
    readonly_fields = ["preview"]

    def preview(self, obj):
        if obj and obj.url:
            return format_html('<img src="{}" style="height:48px;border-radius:8px;object-fit:cover;" />', obj.url)
        return "-"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ["title", "sku", "color", "size", "price", "compare_at_price", "is_active"]


class InventoryInline(admin.StackedInline):
    model = Inventory
    can_delete = False
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["thumb", "title", "source", "category", "price", "currency", "is_featured", "is_trending", "is_active"]
    list_filter = ["source", "category", "brand", "is_featured", "is_trending", "is_active"]
    search_fields = ["title", "sku", "external_id", "short_description"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["category", "brand", "supplier", "tags"]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]
    inlines = [ProductImageInline, ProductVariantInline, InventoryInline]
    actions = ["mark_featured", "mark_trending", "publish", "unpublish"]

    def thumb(self, obj):
        image = obj.primary_image
        if image:
            return format_html('<img src="{}" style="height:42px;width:42px;border-radius:10px;object-fit:cover;" />', image.url)
        return "TIBO"

    @admin.action(description="Mettre en vedette")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Marquer tendance")
    def mark_trending(self, request, queryset):
        queryset.update(is_trending=True)

    @admin.action(description="Publier")
    def publish(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Dépublier")
    def unpublish(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_featured", "is_active", "sort_order"]
    list_filter = ["is_featured", "is_active"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "is_featured", "is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "source", "commission_rate", "is_active"]
    list_filter = ["source", "is_active"]
    search_fields = ["name", "api_shop_domain", "affiliate_tag"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["number", "email", "status", "total", "currency", "created_at"]
    list_filter = ["status", "currency", "created_at"]
    search_fields = ["number", "email", "external_order_id"]
    readonly_fields = ["number", "created_at", "updated_at"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "title", "supplier_source", "quantity", "line_total", "fulfillment_status"]
    list_filter = ["supplier_source", "fulfillment_status"]
    search_fields = ["title", "external_product_id"]


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(ProductReview)
admin.site.register(ProductVariant)
admin.site.register(ProductImage)
admin.site.register(Inventory)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Coupon)
admin.site.register(Payment)
admin.site.register(Address)
admin.site.register(Wishlist)
admin.site.register(AffiliateProfile)
admin.site.register(Commission)
