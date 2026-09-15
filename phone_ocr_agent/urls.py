from django.urls import path

from . import views
from . import job_views

app_name = "phone_ocr_agent"

urlpatterns = [
    path("submit/", job_views.submit, name="submit"),
    path("jobs/<uuid:job_id>/", job_views.status, name="job_status"),
    path("", views.dashboard, name="dashboard"),
    path("export/", views.export_csv, name="export_csv"),
]
