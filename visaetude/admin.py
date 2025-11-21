from django.contrib import admin
from .models import VisaCountry, VisaResource


@admin.register(VisaCountry)
class VisaCountryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(VisaResource)
class VisaResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "country", "category", "resource_type", "order")
    list_filter = ("country", "category", "resource_type")
    search_fields = ("title", "step_label", "url")
    ordering = ("country", "order")
