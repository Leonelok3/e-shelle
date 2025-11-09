# billing/admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription, CreditCode, Transaction

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "duration_days", "price_usd", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("is_active",)
    search_fields = ("name", "slug")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "starts_at", "expires_at", "is_active")
    list_filter = ("plan", "is_active")
    search_fields = ("user__username", "user__email")

@admin.register(CreditCode)
class CreditCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "plan", "is_used", "used_by", "created_at", "used_at")
    list_filter = ("is_used", "plan")
    search_fields = ("code", "used_by__username", "used_by__email")

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "amount", "currency", "description", "created_at", "related_code")
    list_filter = ("type", "currency")
    search_fields = ("user__username", "user__email", "description")
