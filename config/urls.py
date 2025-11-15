# config/urls.py
"""
URL configuration for config project.
Optimisé pour: structure propre, SEO, parcours utilisateur fluide.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Core pages
from core.views import (
    wizard_page, wizard_result_page, wizard_pdf, wizard_steps_page,
    dashboard_page,
)

def home(request):
    return render(request, "home.html")

urlpatterns = [
    # Admin / Home
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    # Auth en premier
    path("authentification/", include("authentification.urls")),

    # Modules
    path("visa-photo/", include("photos.urls")),
    path("cv-generator/", include(("cv_generator.urls", "cv_generator"), namespace="cv_generator")),
    path("motivation/", include("MotivationLetterApp.urls")),
    path("visaetude/", include(("visaetude.urls", "visaetude"), namespace="visaetude")),
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),
    path("prep/", include(("preparation_tests.urls", "preparation_tests"), namespace="preparation_tests")),

    # Placeholders
    #path('visa-travail/', include('work_visa.urls')),
    path("residence-permanente/", home),
    path("visa-tourisme/", home),

    # API / Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/eligibility/", include("eligibility.urls")),
    path("api/radar/", include("radar.urls")),

    # Wizard & Dashboard
    path("wizard/", wizard_page, name="wizard"),
    path("wizard/result/<int:session_id>/", wizard_result_page, name="wizard_result"),
    path("wizard/checklist.pdf", wizard_pdf, name="wizard_pdf"),
    path("wizard/steps/", wizard_steps_page, name="wizard_steps"),
    path("dashboard/", dashboard_page, name="dashboard"),
]

# Fichiers médias en dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
