from django.urls import include, path
from django.http import HttpResponse
from . import job_views

urlpatterns = [path("phone-ocr/", include(([
    path("", lambda request: HttpResponse(), name="dashboard"),
    path("submit/", job_views.submit, name="submit"),
    path("jobs/<uuid:job_id>/", job_views.status, name="job_status"),
], "phone_ocr_agent")))]
