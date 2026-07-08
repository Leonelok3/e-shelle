"""gaz/urls.py"""
from django.urls import path
from . import views

app_name = "gaz"

urlpatterns = [
    path("",                views.accueil,   name="accueil"),
    path("depots/",         views.catalogue, name="catalogue"),
    path("depot/<slug:slug>/", views.detail, name="detail"),
    path("creer-depot/",    views.creer_depot, name="creer_depot"),
]
