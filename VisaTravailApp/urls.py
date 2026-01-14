from django.urls import path
from . import views

app_name = "visa_travail"

urlpatterns = [
    # Parcours principal Visa Travail
    path("", views.home, name="home"),
    path("profil/", views.profil_create, name="profil"),
    path("resultats/<int:profile_id>/", views.resultats, name="resultats"),
    path("plan/<int:profile_id>/", views.plan_action, name="plan_action"),
    path("ressources/", views.ressources, name="ressources"),

    # Vue 360° (coach niveau 7)
    path(
        "profil/<int:profile_id>/vue-360/",
        views.project_overview,
        name="project_overview",
    ),

    # Job board – offres d’emploi enregistrées en base
    path("offres/", views.job_offers_list, name="job_offers_list"),
    path("offres/<int:offer_id>/", views.job_offer_detail, name="job_offer_detail"),

    # Tableau de bord des candidatures (JobApplication)
    path(
        "profil/<int:profile_id>/candidatures/",
        views.job_list,
        name="job_list",
    ),
    path(
        "profil/<int:profile_id>/candidatures/nouvelle/",
        views.job_create,
        name="job_create",
    ),
    path(
        "profil/<int:profile_id>/candidatures/<int:application_id>/",
        views.job_edit,
        name="job_edit",
    ),
    path(
        "profil/<int:profile_id>/offres/<int:offer_id>/candidature/",
        views.job_create_from_offer,
        name="job_create_from_offer",
    ),

    # Coach CV
    path("coach-cv/", views.coach_cv, name="coach_cv"),

    # Export PDF du plan d’action
    path(
        "plan/<int:profile_id>/export-pdf/",
        views.export_plan_pdf,
        name="export_plan_pdf",
    ),
    path("italie-programme/", views.italie_programme, name="italie_programme"),
    path("profil/", views.profil_create, name="profil_create"),

    

]
