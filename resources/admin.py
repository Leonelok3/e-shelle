from django.contrib import admin
from django.utils.html import format_html
from .models import Resource


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display  = ("title", "category", "destination", "resource_type",
                      "file_preview", "is_active", "is_premium", "order", "created_at")
    list_filter   = ("category", "destination", "resource_type", "is_active", "is_premium")
    search_fields = ("title", "description")
    list_editable = ("is_active", "is_premium", "order")
    ordering      = ("order", "-created_at")

    fieldsets = (
        ("Informations principales", {
            "fields": ("title", "description", "category", "destination", "resource_type")
        }),
        ("Fichier", {
            "fields": ("file", "file_size"),
            "description": "Uploadez le fichier directement. La taille sera calculée automatiquement si le champ est vide."
        }),
        ("Publication", {
            "fields": ("is_active", "is_premium", "order")
        }),
    )

    def file_preview(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" style="color:#16a34a;font-weight:600;">⬇ {}</a>',
                obj.file.url,
                obj.get_file_size_display(),
            )
        return format_html('<span style="color:#94a3b8;">— aucun fichier —</span>')

    file_preview.short_description = "Fichier"
