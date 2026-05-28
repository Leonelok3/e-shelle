from django.contrib import admin

from .models import DemandeTravaux, MetierArtisan, ProfilArtisan, RealisationArtisan, VilleArtisan


@admin.register(VilleArtisan)
class VilleArtisanAdmin(admin.ModelAdmin):
    list_display = ("nom", "region", "active", "ordre")
    list_filter = ("active", "region")
    search_fields = ("nom", "region")
    prepopulated_fields = {"slug": ("nom",)}


@admin.register(MetierArtisan)
class MetierArtisanAdmin(admin.ModelAdmin):
    list_display = ("nom", "active", "ordre")
    list_filter = ("active",)
    search_fields = ("nom", "description")
    prepopulated_fields = {"slug": ("nom",)}


class RealisationArtisanInline(admin.TabularInline):
    model = RealisationArtisan
    extra = 1


@admin.register(ProfilArtisan)
class ProfilArtisanAdmin(admin.ModelAdmin):
    list_display = ("nom_public", "ville", "quartier", "compte_type", "est_verifie", "disponible_urgence", "is_active")
    list_filter = ("compte_type", "ville", "est_verifie", "disponible_urgence", "is_active")
    search_fields = ("nom_public", "telephone", "quartier", "description")
    filter_horizontal = ("metiers",)
    prepopulated_fields = {"slug": ("nom_public",)}
    inlines = [RealisationArtisanInline]
    actions = ("activer_verifier", "mettre_business")

    @admin.action(description="Activer et vérifier")
    def activer_verifier(self, request, queryset):
        queryset.update(is_active=True, est_verifie=True)

    @admin.action(description="Mettre en Business")
    def mettre_business(self, request, queryset):
        queryset.update(is_active=True, est_verifie=True, compte_type=ProfilArtisan.TypeCompte.BUSINESS)


@admin.register(DemandeTravaux)
class DemandeTravauxAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "ville", "metier", "besoin", "is_active", "created_at")
    list_filter = ("ville", "metier", "is_active", "created_at")
    search_fields = ("nom", "telephone", "besoin", "description")

