from django.urls import path
from . import views

app_name = "permanent_residence"

urlpatterns = [
    # Page d'accueil du module RP
    path("", views.home_view, name="home"),

    # Simulateur d’éligibilité
    path("eligibilite/", views.eligibility_view, name="eligibility"),
    path("resultat/<int:profile_id>/", views.eligibility_result_view, name="result"),

    # Plan d’action RP
    path("plan/<int:pk>/", views.plan_view, name="plan"),

    # Dashboard RP
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # Stratégies RP
    path("strategies/<int:profile_id>/", views.strategy_view, name="strategy"),

    # Liste et détail des programmes
    path("programmes/", views.program_list_view, name="program_list"),
    path("programmes/<slug:slug>/", views.program_detail_view, name="program_detail"),

    # Coach IA : page HTML (container)
    path("coach/", views.coach_view, name="coach"),

    # Coach IA : API JSON
    path("coach/<int:profile_id>/api/", views.rp_coach_api, name="coach_api"),
   
    path("pr/plan/<int:pk>/", views.plan_view, name="plan_detail"),

]
