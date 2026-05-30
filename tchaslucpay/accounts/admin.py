from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ClientProfile, CollecteurProfile, CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Administration des utilisateurs propres a Tchaslucpay."""

    list_display = ("username", "email", "role", "phone_number", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active", "is_phone_verified")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        ("Tchaslucpay", {"fields": ("role", "phone_number", "is_phone_verified")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Tchaslucpay", {"fields": ("role", "phone_number", "is_phone_verified")}),
    )


@admin.register(CollecteurProfile)
class CollecteurProfileAdmin(admin.ModelAdmin):
    """Administration des collecteurs terrain."""

    list_display = ("employee_code", "user", "zone", "city", "phone_number", "is_active", "created_at")
    list_filter = ("zone", "city", "is_active")
    search_fields = ("employee_code", "user__username", "user__first_name", "user__last_name", "phone_number")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """Administration des clients commercants et de leur solde."""

    list_display = ("account_number", "user", "national_id", "national_id_expiry", "trusted_collecteur", "solde", "city", "quarter", "created_at")
    list_filter = ("city", "trusted_collecteur")
    search_fields = ("account_number", "national_id", "user__username", "user__first_name", "user__last_name", "phone_number")
    autocomplete_fields = ("user", "trusted_collecteur")
    readonly_fields = ("created_at",)
