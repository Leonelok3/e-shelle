"""
URL configuration – VERSION STABLE PRODUCTION
Immigration97
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include

from permanent_residence import views as pr_views

# Core pages
from core.views import (
    wizard_page,
    wizard_result_page,
    wizard_pdf,
    wizard_steps_page,
    dashboard_page,
)

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def home(request):
    return render(request, "home.html")


urlpatterns = [
    # ============================
    # ADMIN & HOME
    # ============================
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    # ============================
    # AUTHENTIFICATION
    # ============================
    path(
        "authentification/",
        include(
            ("authentification.urls", "authentification"),
            namespace="authentification",
        ),
    ),

    # ============================
    # DOCUMENTS
    # ============================
    path("documents/", include("DocumentsApp.urls")),

    # ============================
    # MODULES PRINCIPAUX
    # ============================
    path("visa-photo/", include("photos.urls")),

    path(
        "cv-generator/",
        include(("cv_generator.urls", "cv_generator"), namespace="cv_generator"),
    ),

    path("motivation/", include("MotivationLetterApp.urls")),
    path("visa-etudes/", include("visaetude.urls")),

    path(
        "billing/",
        include(("billing.urls", "billing"), namespace="billing"),
    ),

    # ============================
    # ✅ PREPARATION TESTS (UNE SEULE FOIS – CORRECT)
    # ============================
    path(
        "prep/",
        include(
            ("preparation_tests.urls", "preparation_tests"),
            namespace="preparation_tests",
        ),
    ),

    # ============================
    # VISAS
    # ============================
    path("visa-travail/", include("VisaTravailApp.urls")),
    path("visa-tourisme/", include("VisaTourismeApp.urls")),

    # ============================
    # RÉSIDENCE PERMANENTE
    # ============================
    path(
        "residence-permanente/",
        pr_views.home_view,
        name="residence_permanente",
    ),
    path("rp/", pr_views.home_view, name="rp_shortcut"),
    path("pr/", include("permanent_residence.urls")),

    # ============================
    # API & DOC
    # ============================
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/eligibility/", include("eligibility.urls")),
    path("api/radar/", include("radar.urls")),

    # ============================
    # WIZARD & DASHBOARD
    # ============================
    path("wizard/", wizard_page, name="wizard"),
    path(
        "wizard/result/<int:session_id>/",
        wizard_result_page,
        name="wizard_result",
    ),
    path("wizard/checklist.pdf", wizard_pdf, name="wizard_pdf"),
    path("wizard/steps/", wizard_steps_page, name="wizard_steps"),
    path("dashboard/", dashboard_page, name="dashboard"),

    # ============================
    # LANGUES
    # ============================
    path(
        "langue/english/",
        include(("EnglishPrepApp.urls", "englishprep"), namespace="englishprep"),
    ),
    path(
        "langue/german/",
        include(("GermanPrepApp.urls", "germanprep"), namespace="germanprep"),
    ),

    # ============================
    # PROFILES
    # ============================
    path("profiles/", include("profiles.urls")),
   

    # ============================
    # 2FA (DÉSACTIVÉ)
    # ============================
    # path("account/", include("two_factor.urls")),
]

# ============================
# MEDIA EN DEBUG
# ============================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
