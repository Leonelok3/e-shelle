from django.urls import path
from . import views

app_name = "visaetude"

urlpatterns = [

    # Pages principales
    path("", views.home, name="home"),
    path("profil/", views.profile, name="profile"),
    path("pays/", views.countries_list, name="countries_list"),
    path("pays/<str:country>/", views.country_detail, name="country_detail"),

    # Parcours & checklist
    path("parcours/", views.roadmap, name="roadmap"),
    path("checklist/", views.checklist, name="checklist"),

    # Coach IA
    path("coach/", views.coach_ai, name="coach_ai"),
    path("coach-api/", views.coach_ai_api, name="coach_ai_api"),

    # Ressource vidéo / PDF
    path("resource/<int:resource_id>/", views.resource_view, name="resource_view"),
]
