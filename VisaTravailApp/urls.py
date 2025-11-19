from django.urls import path
from . import views

app_name = "visa_travail"

urlpatterns = [
    path("", views.home, name="home"),
    path("profil/", views.profil_create, name="profil"),
    path("resultats/<int:profile_id>/", views.resultats, name="resultats"),
    path("plan/<int:profile_id>/", views.plan_action, name="plan_action"),
    path("plan/<int:profile_id>/export-pdf/", views.export_plan_pdf, name="export_plan_pdf"),

    # Coach CV
    path("coach-cv/", views.coach_cv, name="coach_cv"),

    # Job tracker (candidatures personnelles)
    path("profil/<int:profile_id>/candidatures/", views.job_list, name="job_list"),
    path("profil/<int:profile_id>/candidatures/nouvelle/", views.job_create, name="job_create"),
    path("candidatures/<int:job_id>/modifier/", views.job_update, name="job_update"),
    path("candidatures/<int:job_id>/statut/", views.job_update_status, name="job_update_status"),

    # Job board public
    path("offres/", views.job_offers_list, name="job_offers_list"),
    path("offres/<int:offer_id>/", views.job_offer_detail, name="job_offer_detail"),
    path("offres/<int:offer_id>/ajouter/", views.job_create_from_offer, name="job_create_from_offer"),

    path("ressources/", views.ressources, name="ressources"),
]
