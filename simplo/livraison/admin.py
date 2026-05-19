from django.contrib import admin

from .models import DeliveryRequest


@admin.register(DeliveryRequest)
class DeliveryRequestAdmin(admin.ModelAdmin):
    list_display = ("ville", "quartier_ramassage", "quartier_livraison", "statut", "created_at")
    list_filter = ("ville", "statut")
    search_fields = ("quartier_ramassage", "quartier_livraison", "description_colis")
