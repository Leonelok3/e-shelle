from django.urls import path

from . import views

app_name = "phone_ocr_agent"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("export/", views.export_csv, name="export_csv"),
]
