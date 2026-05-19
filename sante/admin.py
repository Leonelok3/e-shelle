from django.contrib import admin

from .models import CategorieSante, DemandeSante, ProduitSante, ProfessionnelSante, VilleSante


@admin.register(VilleSante)
class VilleSanteAdmin(admin.ModelAdmin):
    list_display = ("nom", "region", "active", "ordre")
    list_filter = ("active", "region")
    search_fields = ("nom", "region")
    prepopulated_fields = {"slug": ("nom",)}


@admin.register(CategorieSante)
class CategorieSanteAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_categorie", "active", "ordre")
    list_filter = ("type_categorie", "active")
    search_fields = ("nom",)
    prepopulated_fields = {"slug": ("nom",)}


@admin.register(ProfessionnelSante)
class ProfessionnelSanteAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_pro", "ville", "telephone", "is_active", "is_verified", "is_featured")
    list_filter = ("type_pro", "ville", "is_active", "is_verified", "is_featured", "urgence", "teleconsultation")
    search_fields = ("nom", "telephone", "quartier", "adresse")
    filter_horizontal = ("specialites",)
    prepopulated_fields = {"slug": ("nom",)}
    actions = ("activer", "mettre_en_vedette")

    @admin.action(description="Activer et vérifier")
    def activer(self, request, queryset):
        queryset.update(is_active=True, is_verified=True)

    @admin.action(description="Mettre en vedette")
    def mettre_en_vedette(self, request, queryset):
        queryset.update(is_featured=True, is_active=True, is_verified=True)


@admin.register(ProduitSante)
class ProduitSanteAdmin(admin.ModelAdmin):
    list_display = ("titre", "type_produit", "ville", "prix", "stock_disponible", "is_active", "is_verified", "is_featured")
    list_filter = ("type_produit", "ville", "livraison", "ordonnance_requise", "is_active", "is_verified", "is_featured")
    search_fields = ("titre", "vendeur_nom", "telephone", "description")
    prepopulated_fields = {"slug": ("titre",)}
    actions = ("activer", "mettre_en_vedette")

    @admin.action(description="Activer et vérifier")
    def activer(self, request, queryset):
        queryset.update(is_active=True, is_verified=True)

    @admin.action(description="Mettre en vedette")
    def mettre_en_vedette(self, request, queryset):
        queryset.update(is_featured=True, is_active=True, is_verified=True)


@admin.register(DemandeSante)
class DemandeSanteAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "ville", "besoin", "is_active", "created_at")
    list_filter = ("ville", "is_active", "created_at")
    search_fields = ("nom", "telephone", "besoin", "message")
