from django.contrib import admin

from .models import MotoRequest


@admin.register(MotoRequest)
class MotoRequestAdmin(admin.ModelAdmin):
    list_display = ("ville", "quartier_depart", "destination", "statut", "created_at")
    list_filter = ("ville", "statut")
    search_fields = ("quartier_depart", "destination", "note")
