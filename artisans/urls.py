from django.urls import path

from . import views

app_name = "artisans"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("artisan/<slug:slug>/", views.detail_artisan, name="detail_artisan"),
    path("demande/", views.demande_travaux, name="demande_travaux"),
    path("espace/", views.espace_artisan, name="espace_artisan"),
]
