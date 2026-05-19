from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ClientProfile, CustomUser, PrestataireProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "phone_number", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Simplo", {"fields": ("role", "phone_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Simplo", {"fields": ("role", "phone_number", "first_name", "last_name")}),
    )


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "ville", "quartier", "created_at")
    search_fields = ("nom", "telephone", "ville", "quartier")
    list_filter = ("ville", "quartier")


@admin.register(PrestataireProfile)
class PrestataireProfileAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "telephone",
        "ville",
        "quartier_base",
        "type_service",
        "statut",
        "nombre_courses",
        "is_verified",
        "is_active",
    )
    search_fields = ("nom", "telephone", "ville", "quartier_base", "zone_couverte")
    list_filter = ("type_service", "statut", "ville", "is_verified", "is_active")
