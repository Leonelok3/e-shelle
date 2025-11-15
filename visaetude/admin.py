# visaetude/admin.py
from django.contrib import admin
from .models import (
    Country, CountryGuide, RequiredDocument,
    UserProfile, UserChecklist, FAQ, Milestone
)

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("nom", "code", "actif", "delai_traitement", "cout_visa", "taux_acceptation")
    list_filter = ("actif",)
    search_fields = ("nom", "code")

@admin.register(CountryGuide)
class CountryGuideAdmin(admin.ModelAdmin):
    list_display = ("pays", "titre")
    search_fields = ("titre", "pays__nom")
    autocomplete_fields = ("pays",)

@admin.register(RequiredDocument)
class RequiredDocumentAdmin(admin.ModelAdmin):
    list_display = ("pays", "nom", "obligatoire")
    list_filter = ("obligatoire", "pays")
    search_fields = ("nom", "pays__nom")
    autocomplete_fields = ("pays",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "pays_origine", "niveau_etude", "budget_disponible")
    search_fields = ("user__username", "user__email")
    # ✅ Seuls les champs FK/M2M sont autorisés ici
    autocomplete_fields = ("user",)
    # Si beaucoup d'utilisateurs: active aussi raw_id_fields
    # raw_id_fields = ("user",)

@admin.register(UserChecklist)
class UserChecklistAdmin(admin.ModelAdmin):
    list_display = ("user", "pays", "document", "statut", "date_modification")
    list_filter = ("statut", "pays")
    search_fields = ("user__username", "document__nom")
    autocomplete_fields = ("user", "pays", "document")
    date_hierarchy = "date_modification"

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("pays", "question", "populaire")
    list_filter = ("populaire", "pays")
    search_fields = ("question",)
    autocomplete_fields = ("pays",)

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("pays", "titre", "ordre")
    list_editable = ("ordre",)
    search_fields = ("titre",)
    autocomplete_fields = ("pays",)
