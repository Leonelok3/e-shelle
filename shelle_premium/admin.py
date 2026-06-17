from django.contrib import admin

from .models import Prestataire


@admin.register(Prestataire)
class PrestataireAdmin(admin.ModelAdmin):
    """Administration Django des prestataires Shelle Premium."""

    list_display = ["nom_complet", "code_premium", "date_expiration", "statut", "date_inscription"]
    search_fields = ["nom_complet", "code_premium", "adresse"]
    list_filter = ["date_inscription"]
    readonly_fields = ["date_inscription"]

    def statut(self, obj):
        """Affiche le statut calcule dans l'admin Django."""

        return "Actif" if obj.est_actif() else "Expire"

    statut.short_description = "Statut"

