from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from django.shortcuts import render

def about_page(request):
    return render(request, "about.html")

def services_page(request):
    return render(request, "services.html")
from permanent_residence import views as pr_views
from core.views import (
    wizard_page,
    wizard_result_page,
    wizard_pdf,
    wizard_steps_page,
    dashboard_page,
)

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from django.contrib.sitemaps.views import sitemap
from actualite.sitemaps import NewsItemSitemap


def home(request):
    return render(request, "home.html")


sitemaps = {"actualite": NewsItemSitemap}


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    path(
        "authentification/",
        include(("authentification.urls", "authentification"), namespace="authentification"),
    ),

    path("documents/", include("DocumentsApp.urls")),

    path("visa-photo/", include("photos.urls")),

    path(
        "cv-generator/",
        include(("cv_generator.urls", "cv_generator"), namespace="cv_generator"),
    ),

    path(
        "motivation/",
        include(("MotivationLetterApp.urls", "motivation_letter"), namespace="motivation_letter"),
    ),

    path("visa-etudes/", include("visaetude.urls")),

    path("billing/", include(("billing.urls", "billing"), namespace="billing")),

    path(
        "prep/",
        include(("preparation_tests.urls", "preparation_tests"), namespace="preparation_tests"),
    ),

    path("visa-travail/", include("VisaTravailApp.urls")),
    path("visa-tourisme/", include("VisaTourismeApp.urls")),

    path("residence-permanente/", pr_views.home_view, name="residence_permanente"),
    path("rp/", pr_views.home_view, name="rp_shortcut"),
    path("pr/", include("permanent_residence.urls")),

    path("actualite/", include(("actualite.urls", "actualite"), namespace="actualite")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/eligibility/", include("eligibility.urls")),
    path("api/radar/", include("radar.urls")),

    path("wizard/", wizard_page, name="wizard"),
    path("wizard/result/<int:session_id>/", wizard_result_page, name="wizard_result"),
    path("wizard/checklist.pdf", wizard_pdf, name="wizard_pdf"),
    path("wizard/steps/", wizard_steps_page, name="wizard_steps"),
    path("dashboard/", dashboard_page, name="dashboard"),

    path("langue/english/", include(("EnglishPrepApp.urls", "englishprep"), namespace="englishprep")),
    path("langue/german/", include(("GermanPrepApp.urls", "germanprep"), namespace="germanprep")),

    path("profiles/", include("profiles.urls")),

    path("italien/", include("italian_courses.urls")),

    path("jobs/", include(("job_agent.urls", "job_agent"), namespace="job_agent")),
    path("about/", about_page, name="about"),
    path("services/", services_page, name="services"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
