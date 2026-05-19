from django.urls import path

from . import views

app_name = "simplo_marketplace"

urlpatterns = [
    path("", views.home, name="home"),
    path("prestataires/", views.provider_list, name="provider_list"),
]
