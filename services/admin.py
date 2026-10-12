"""
services/admin.py — Admin panel pour les Services E-Shelle
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import OffreService, CategoriePortfolio, ProjetPortfolio, Devis, ContactMessage


@admin.register(OffreService)
class OffreServiceAdmin(admin.ModelAdmin):
    list_display  = ("icone", "titre", "prix_affiche", "delai_jours", "is_active", "is_featured", "ordre")
    list_editable = ("is_active", "is_featured", "ordre")
    prepopulated_fields = {"slug": ("titre",)}
    fieldsets = (
        ("Contenu français", {"fields": ("titre", "description", "features")}),
        ("English content", {"fields": ("titre_en", "description_en", "features_en"), "classes": ("collapse",)}),
        ("Offre", {"fields": ("slug", "icone", "prix_base", "delai_jours", "is_active", "is_featured", "ordre")}),
    )

    def prix_affiche(self, obj):
        return obj.prix_affiche
    prix_affiche.short_description = "Prix"


@admin.register(CategoriePortfolio)
class CategoriePortfolioAdmin(admin.ModelAdmin):
    list_display  = ("nom", "slug", "ordre")
    list_editable = ("ordre",)
    prepopulated_fields = {"slug": ("nom",)}
    fields = ("nom", "nom_en", "slug", "ordre")


@admin.register(ProjetPortfolio)
class ProjetPortfolioAdmin(admin.ModelAdmin):
    list_display  = ("image_preview", "titre", "categorie", "client", "is_published", "is_featured", "ordre")
    list_filter   = ("categorie", "is_published", "is_featured")
    list_editable = ("is_published", "is_featured", "ordre")
    search_fields = ("titre", "description", "client")
    prepopulated_fields = {"slug": ("titre",)}
    fieldsets = (
        ("Contenu français", {"fields": ("titre", "description")}),
        ("English content", {"fields": ("titre_en", "description_en"), "classes": ("collapse",)}),
        ("Projet", {"fields": ("slug", "image", "categorie", "technologies", "lien_demo", "lien_code", "client", "is_published", "is_featured", "ordre")}),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="50" style="object-fit:cover;border-radius:4px">', obj.image.url)
        return "—"
    image_preview.short_description = "Aperçu"


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display  = ("nom", "email", "type_projet", "budget", "montant_estime_affiche", "statut", "created_at")
    list_filter   = ("statut", "type_projet", "budget")
    search_fields = ("nom", "email", "description")
    list_editable = ("statut",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    fieldsets = (
        ("Contact", {
            "fields": ("nom", "email", "telephone", "entreprise", "utilisateur")
        }),
        ("Projet", {
            "fields": ("type_projet", "budget", "delai_souhaite", "description", "config_data")
        }),
        ("Suivi", {
            "fields": ("statut", "montant_estime", "note_interne", "created_at", "updated_at")
        }),
    )

    def montant_estime_affiche(self, obj):
        if obj.montant_estime:
            return f"{int(obj.montant_estime):,} FCFA".replace(",", " ")
        return "—"
    montant_estime_affiche.short_description = "Montant estimé"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ("nom", "email", "sujet", "lu", "repondu", "created_at")
    list_filter   = ("sujet", "lu", "repondu")
    list_editable = ("lu", "repondu")
    search_fields = ("nom", "email", "message")
    readonly_fields = ("created_at",)
