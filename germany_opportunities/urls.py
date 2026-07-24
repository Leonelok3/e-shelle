from django.urls import path
from . import views

app_name = "germany_opportunities"

urlpatterns = [
    path("",                       views.catalogue,       name="catalogue"),
    path("offre/<int:pk>/",        views.offer_detail,    name="offer_detail"),
    path("offre/<int:pk>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("offre/<int:pk>/applied/",  views.mark_applied,    name="mark_applied"),
    path("mes-favoris/",           views.my_bookmarks,    name="my_bookmarks"),
    path("candidats/",             views.candidate_profiles, name="candidate_profiles"),
    path("entreprises/",           views.top_companies,   name="top_companies"),
    path("premium/",               views.premium_pricing, name="premium_pricing"),
    path("simulation/",            views.interview_simulator_hub, name="interview_simulator_hub"),
    path("simulation/demarrer/",   views.start_interview_simulation, name="start_interview_simulation"),
    path("simulation/<int:pk>/",   views.interview_simulation_detail, name="interview_simulation_detail"),
    path("simulation/<int:pk>/message/", views.interview_simulation_message, name="interview_simulation_message"),
    path("simulation/<int:pk>/evaluer/", views.interview_simulation_evaluate, name="interview_simulation_evaluate"),
]
