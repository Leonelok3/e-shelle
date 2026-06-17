from django.urls import path

from . import views

app_name = "lebelage_importer"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
