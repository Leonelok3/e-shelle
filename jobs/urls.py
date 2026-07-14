from django.urls import path
from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("offres/", views.catalogue, name="catalogue"),
    path("publier/", views.publier, name="publier"),
    path("offre/<slug:slug>/", views.detail, name="detail"),
    path("canada/", views.canada_jobs, name="canada_jobs"),
    path("canada/bourses/", views.canada_scholarships, name="canada_scholarships"),
    path("canada/visitor-opportunites/", views.canada_visitor_opps, name="canada_visitor_opps"),
]
