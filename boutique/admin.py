"""
boutique/admin.py — Admin panel pour la Boutique Digitale
Gestion produits, commandes, téléchargements depuis /admin/
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CategorieProduit, Produit, ImageProduit, AvisProduit,
    Panier, LignePanier, Commande, LigneCommande, Telechargement
)


@admin.register(CategorieProduit)
class CategorieProduitAdmin(admin.ModelAdmin):
    list_display  = ("icone", "nom", "slug", "ordre", "active")
    list_editable = ("ordre", "active")
    prepopulated_fields = {"slug": ("nom",)}


class ImageProduitInline(admin.TabularInline):
    model = ImageProduit
    extra = 2
    fields = ("image", "alt", "ordre")


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display  = (
        "thumbnail_preview", "titre", "type_produit", "categorie",
        "prix_affiche", "nb_ventes", "note_moyenne", "is_published", "is_featured"
    )
    list_filter   = ("is_published", "is_featured", "is_gratuit", "type_produit", "categorie")
    search_fields = ("titre", "description")
    list_editable = ("is_published", "is_featured")
    prepopulated_fields = {"slug": ("titre",)}
    inlines = [ImageProduitInline]
    fieldsets = (
        ("Informations produit", {
            "fields": ("titre", "slug", "type_produit", "categorie", "vendeur",
                       "description", "description_courte", "thumbnail", "tags")
        }),
        ("Fichier / Livraison", {
            "fields": ("fichier", "url_externe")
        }),
        ("Prix et publication", {
            "fields": ("prix", "prix_barre", "is_gratuit", "is_published", "is_featured")
        }),
        ("Statistiques", {
            "fields": ("nb_ventes", "note_moyenne", "nb_avis"),
            "classes": ("collapse",)
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="60" height="45" style="object-fit:cover;border-radius:4px">',
                obj.thumbnail.url
            )
        return "—"
    thumbnail_preview.short_description = "Aperçu"

    def prix_affiche(self, obj):
        if obj.is_gratuit or obj.prix == 0:
            return format_html('<span style="color:#4CAF50;font-weight:600">{}</span>', 'Gratuit')
        return f"{int(obj.prix):,} FCFA".replace(",", " ")
    prix_affiche.short_description = "Prix"


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0
    readonly_fields = ("produit", "quantite", "prix_unit", "sous_total")


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display  = ("reference", "utilisateur", "statut", "montant_total", "created_at")
    list_filter   = ("statut",)
    search_fields = ("reference", "utilisateur__username", "email_acheteur")
    list_editable = ("statut",)
    readonly_fields = ("reference", "created_at", "updated_at")
    inlines = [LigneCommandeInline]
    date_hierarchy = "created_at"

    def montant_total(self, obj):
        return f"{int(obj.montant_total):,} FCFA".replace(",", " ")


@admin.register(Telechargement)
class TelechargementAdmin(admin.ModelAdmin):
    list_display  = ("utilisateur", "produit", "nb_telechargements", "max_telechargements",
                      "est_valide_display", "created_at")
    list_filter   = ("produit",)
    search_fields = ("utilisateur__username", "produit__titre")
    readonly_fields = ("token", "created_at")

    def est_valide_display(self, obj):
        if obj.est_valide:
            return format_html('<span style="color:#4CAF50">{}</span>', '✓ Valide')
        return format_html('<span style="color:#EF5350">{}</span>', '✗ Expiré')
    est_valide_display.short_description = "Statut"


@admin.register(AvisProduit)
class AvisProduitAdmin(admin.ModelAdmin):
    list_display  = ("utilisateur", "produit", "note", "titre", "created_at")
    list_filter   = ("note", "produit")
    search_fields = ("utilisateur__username", "commentaire")
