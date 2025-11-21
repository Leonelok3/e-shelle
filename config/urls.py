# config/urls.py
"""
URL configuration for config project.
Optimisé : structure propre, SEO, hiérarchie claire, URLs logiques.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include

from permanent_residence import views as pr_views

# Core pages
from core.views import (
    wizard_page, wizard_result_page, wizard_pdf, wizard_steps_page,
    dashboard_page,
)

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def home(request):
    return render(request, "home.html")


# ------------------ URLS PRINCIPALES ------------------ #
urlpatterns = [

    # ----- ADMIN + PAGE D’ACCUEIL ----- #
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    # ----- AUTHENTIFICATION ----- #
    path("authentification/", include("authentification.urls")),


    # ------------------ MODULES PRINCIPAUX ------------------ #
    path("visa-photo/", include("photos.urls")),
    path("cv-generator/", include(("cv_generator.urls", "cv_generator"), namespace="cv_generator")),
    path("motivation/", include("MotivationLetterApp.urls")),
    path("visaetude/", include(("visaetude.urls", "visaetude"), namespace="visaetude")),
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),
    path("prep/", include(("preparation_tests.urls", "preparation_tests"), namespace="preparation_tests")),
    path("prep/en/", include(("english_tests.urls", "english_tests"), namespace="english_tests")),
    #path("german/", include("german_tests.urls")),
    path("visa-travail/", include("VisaTravailApp.urls")),


    # ------------------ RÉSIDENCE PERMANENTE (NOUVEAU MODULE) ------------------ #
    # 1) URL marketing propre
    path(
        "residence-permanente/",
        pr_views.home_view,
        name="residence_permanente",
    ),
    # 2) URLs internes du module
    path("rp/", pr_views.home_view, name="rp_shortcut"),

    path("pr/", include("permanent_residence.urls")),


    # ------------------ API & DOCUMENTATION ------------------ #
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/eligibility/", include("eligibility.urls")),
    path("api/radar/", include("radar.urls")),


    # ------------------ WIZARD & DASHBOARD ------------------ #
    path("wizard/", wizard_page, name="wizard"),
    path("wizard/result/<int:session_id>/", wizard_result_page, name="wizard_result"),
    path("wizard/checklist.pdf", wizard_pdf, name="wizard_pdf"),
    path("wizard/steps/", wizard_steps_page, name="wizard_steps"),

    path("dashboard/", dashboard_page, name="dashboard"),
]


# ------------------ MÉDIA EN MODE DÉVELOPPEMENT ------------------ #
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
