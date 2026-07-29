"""
formations/admin.py — Admin panel pour le module Formation
Permet de créer et gérer cours, leçons, quiz directement depuis /admin/
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    Categorie, Formation, Chapitre, Lecon, Quiz, Question,
    ResultatQuiz, Inscription, Progression, AvisFormation, Certificat
)


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display  = ("icone", "nom", "slug", "ordre", "active")
    list_editable = ("ordre", "active")
    prepopulated_fields = {"slug": ("nom",)}
    ordering = ["ordre", "nom"]


class ChapitreInline(admin.TabularInline):
    model = Chapitre
    extra = 1
    fields = ("titre", "ordre", "description")
    ordering = ["ordre"]


class LeconInline(admin.TabularInline):
    model = Lecon
    extra = 1
    fields = ("titre", "type_lecon", "ordre", "duree", "is_free", "is_published")
    ordering = ["ordre"]


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail_preview", "titre", "categorie", "niveau", "langue",
        "prix_affiche", "nb_inscrits", "is_published", "is_featured"
    )
    list_filter   = ("is_published", "is_featured", "categorie", "niveau", "langue")
    search_fields = ("titre", "description")
    list_editable = ("is_published", "is_featured")
    prepopulated_fields = {"slug": ("titre",)}
    inlines = [ChapitreInline]
    fieldsets = (
        ("Informations générales", {
            "fields": ("titre", "slug", "categorie", "formateur", "description",
                       "description_courte", "thumbnail", "video_intro")
        }),
        ("Paramètres pédagogiques", {
            "fields": ("niveau", "langue", "objectifs", "prerequis", "duree_totale")
        }),
        ("Prix et publication", {
            "fields": ("prix", "prix_barre", "is_published", "is_featured")
        }),
        ("Statistiques (auto)", {
            "fields": ("nb_lecons", "nb_inscrits", "note_moyenne"),
            "classes": ("collapse",)
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="60" height="40" style="object-fit:cover;border-radius:4px">', obj.thumbnail.url)
        return "—"
    thumbnail_preview.short_description = "Aperçu"

    def prix_affiche(self, obj):
        if obj.est_gratuite:
            return mark_safe('<span style="color:#4CAF50;font-weight:600">Gratuit</span>')
        return format_html('{} FCFA', int(obj.prix))
    prix_affiche.short_description = "Prix"


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ("texte", "type_q", "choix", "reponse_correcte", "explication", "points", "ordre")
    ordering = ["ordre"]


@admin.register(Chapitre)
class ChapitreAdmin(admin.ModelAdmin):
    list_display  = ("formation", "titre", "ordre")
    list_filter   = ("formation",)
    search_fields = ("titre", "formation__titre")
    ordering      = ["formation", "ordre"]
    inlines       = [LeconInline]


@admin.register(Lecon)
class LeconAdmin(admin.ModelAdmin):
    list_display  = ("titre", "chapitre", "type_lecon", "duree", "is_free", "is_published", "ordre")
    list_filter   = ("type_lecon", "is_free", "is_published", "chapitre__formation")
    search_fields = ("titre", "contenu", "chapitre__formation__titre")
    list_editable = ("is_published", "is_free", "ordre")
    ordering      = ["chapitre", "ordre"]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("titre", "lecon", "formation", "score_min", "actif")
    list_filter  = ("actif",)
    search_fields = ("titre",)
    inlines = [QuestionInline]


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display  = ("utilisateur", "formation", "date_inscription", "progression_pct", "termine")
    list_filter   = ("termine", "formation")
    search_fields = ("utilisateur__username", "formation__titre")
    date_hierarchy = "date_inscription"


@admin.register(ResultatQuiz)
class ResultatQuizAdmin(admin.ModelAdmin):
    list_display  = ("utilisateur", "quiz", "score", "nb_bonnes", "nb_questions", "termine", "created_at")
    list_filter   = ("termine",)
    search_fields = ("utilisateur__username", "quiz__titre")


@admin.register(AvisFormation)
class AvisFormationAdmin(admin.ModelAdmin):
    list_display  = ("utilisateur", "formation", "note", "created_at")
    list_filter   = ("note", "formation")
    search_fields = ("utilisateur__username", "commentaire")


@admin.register(Certificat)
class CertificatAdmin(admin.ModelAdmin):
    list_display  = ("code_unique", "utilisateur", "formation", "date_obtenu")
    search_fields = ("code_unique", "utilisateur__username")
    readonly_fields = ("code_unique", "date_obtenu")
