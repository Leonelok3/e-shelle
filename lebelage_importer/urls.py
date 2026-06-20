from django.urls import path

from . import views

app_name = "lebelage_importer"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("download/<str:bucket>/<str:file_format>/", views.download_export, name="download_export"),
]
