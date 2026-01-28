from django.contrib import admin
from .models import ProtectionProtocol

@admin.register(ProtectionProtocol)
class ProtectionProtocolAdmin(admin.ModelAdmin):
    list_display = ("title", "version", "is_active", "published_at")
    list_filter = ("is_active",)
    search_fields = ("title", "content")
    readonly_fields = ("created_at", "updated_at")
