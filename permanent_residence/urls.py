# permanent_residence/urls.py
from django.urls import path
from . import views

app_name = "permanent_residence"

urlpatterns = [
    path("", views.home_view, name="home"),

    # Simulateur d’éligibilité
    path("eligibility/", views.eligibility_view, name="eligibility"),

    # Plan d’action RP
    path("plan/<int:profile_id>/", views.plan_view, name="plan"),

    # Coach IA (page + API)
    path("coach/", views.coach_view, name="coach"),
    path("coach/api/<int:profile_id>/", views.rp_coach_api, name="coach_api"),

    # Liste / fiche programmes
    path("programmes/", views.program_list_view, name="program_list"),
    path("programmes/<slug:slug>/", views.program_detail_view, name="program_detail"),
]
