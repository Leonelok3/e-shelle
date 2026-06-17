from django.urls import path

from . import views


app_name = "shelle_premium"

urlpatterns = [
    path("shelle-premium/", views.formulaire, name="formulaire"),
    path("admin-shelle/", views.dashboard, name="dashboard"),
    path("admin-shelle/export/", views.export_csv, name="export_csv"),
]

