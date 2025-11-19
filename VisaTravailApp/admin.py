from django.contrib import admin
from .models import UserProfile, ActionStep, VisaOption, JobApplication, JobOffer


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nom",
        "email",
        "pays_residence",
        "pays_cibles",
        "domaine_metier",
        "niveau_etudes",
        "annees_experience",
        "date_creation",
    )
    search_fields = ("nom", "email", "pays_residence", "pays_cibles", "domaine_metier")
    list_filter = ("pays_residence", "niveau_etudes", "horizon_depart")


@admin.register(ActionStep)
class ActionStepAdmin(admin.ModelAdmin):
    list_display = ("id", "user_profile", "titre", "statut", "ordre")
    list_filter = ("statut",)
    search_fields = ("titre", "description")


@admin.register(VisaOption)
class VisaOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "pays", "nom_programme", "difficulte", "delai_approx")
    search_fields = ("pays", "nom_programme")
    list_filter = ("pays", "difficulte")


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "titre_poste", "entreprise", "pays", "statut", "user_profile")
    list_filter = ("pays", "statut")
    search_fields = ("titre_poste", "entreprise", "pays", "user_profile__nom")


@admin.register(JobOffer)
class JobOfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "titre",
        "entreprise",
        "pays",
        "ville",
        "type_contrat",
        "est_active",
        "date_publication",
    )
    list_filter = ("pays", "type_contrat", "est_active")
    search_fields = ("titre", "entreprise", "pays", "ville", "domaine")
    ordering = ("priorite", "-date_publication")
