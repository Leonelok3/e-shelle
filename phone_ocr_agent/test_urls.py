from django.urls import include, path
from django.http import HttpResponse
from .access import staff_only_noindex
from . import job_views

urlpatterns = [path("phone-ocr/", include(([
    path("", staff_only_noindex(lambda request: HttpResponse()), name="dashboard"),
    path("submit/", job_views.submit, name="submit"),
    path("jobs/<uuid:job_id>/", job_views.status, name="job_status"),
], "phone_ocr_agent")))]
