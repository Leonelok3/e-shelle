"""
AdGen — Administration Django
"""
from django.contrib import admin
from .models import AdCampaign, AdContent, AdModule, AdUsageStat


class AdContentInline(admin.StackedInline):
    model  = AdContent
    extra  = 0
    fields = ("titles", "description_generated", "benefits",
              "facebook_post", "instagram_post", "whatsapp_message",
              "tiktok_script", "chatbot_reply", "tokens_used", "generated_at")
    readonly_fields = ("generated_at", "tokens_used")


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display   = ("nom_produit", "user", "pays", "ville", "has_photo", "status", "modules_selected", "created_at")
    list_filter    = ("status", "pays", "ville", "created_at")
    search_fields  = ("nom_produit", "ville", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    inlines        = [AdContentInline]

    fieldsets = (
        ("Produit", {"fields": ("user", "nom_produit", "description", "photo_produit", "prix", "cible", "pays", "ville")}),
        ("Configuration", {"fields": ("modules_selected", "status")}),
        ("Méta", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Photo", boolean=True)
    def has_photo(self, obj):
        return bool(obj.photo_produit)


@admin.register(AdModule)
class AdModuleAdmin(admin.ModelAdmin):
    list_display       = ("order", "icon", "name", "slug", "is_active", "is_premium")
    list_display_links = ("name",)
    list_editable      = ("is_active", "is_premium", "order")
    list_filter   = ("is_active", "is_premium")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order"]


@admin.register(AdContent)
class AdContentAdmin(admin.ModelAdmin):
    list_display  = ("campaign", "tokens_used", "generated_at")
    readonly_fields = ("generated_at", "tokens_used", "raw_json")
    search_fields = ("campaign__nom_produit",)


@admin.register(AdUsageStat)
class AdUsageStatAdmin(admin.ModelAdmin):
    list_display  = ("user", "campaigns_count", "tokens_total", "last_generation")
    readonly_fields = ("last_generation",)
    search_fields = ("user__username", "user__email")
