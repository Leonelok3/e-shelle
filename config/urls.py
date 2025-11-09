"""
URL configuration for config project.
Optimisé pour: structure propre, SEO, parcours utilisateur fluide.
"""
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.views import wizard_steps_page 
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include
from core.views import wizard_page, wizard_result_page, wizard_pdf
from core.views import dashboard_page
from django.urls import path, include
from core.views import dashboard_page
def home(request):
    return render(request, "home.html")


urlpatterns = [
    # ✅ ADMIN
    path("admin/", admin.site.urls),

    # ✅ CV GENERATOR (placé en haut pour reconnaissance des namespaces)
    path("cv-generator/", include(("cv_generator.urls", "cv_generator"), namespace="cv_generator")),

    # ✅ HOME
    path("", home, name="home"),

    # ✅ MODULE PHOTO VISA (DV Lottery)
    path("visa-photo/", include("photos.urls")),
    

    # ✅ MODULES IMMIGRATION (Placeholder pour le futur)
    path('motivation/', include('MotivationLetterApp.urls')),  # ← AJOUT
    path("visa-tourisme/", home),
    path("visa-etudes/", home),
    path("visa-travail/", home),
    path("prep-langues/", home),
    path("residence-permanente/", home),
  
      # ... tes autres routes ...
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/eligibility/", include("eligibility.urls")),

    # ✅ BILLING / PAYMENTS
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),

    # ✅ CUSTOM AUTH SYSTEM (ton app)
    # Important: on place TOUJOURS l'app authentification AVANT Django auth/url par défaut
    path("authentification/", include("authentification.urls")),  

    # ❌ SUPPRIMÉ: path("accounts/", include("django.contrib.auth.urls"))
    # Django cherchait registration/login.html et créait l’erreur

    # ✅ LOGIN Django mais avec ton template
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='account/login.html'),
        name='login'
    ),

    # ✅ Django-Allauth (on garde pour le futur Google / Facebook login)
    path("accounts/", include("allauth.urls")),

     # ... tes autres routes ...
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/eligibility/", include("eligibility.urls")),



     # ... tes routes déjà présentes ...
    path("wizard/", wizard_page, name="wizard"),
    path("wizard/result/<int:session_id>/", wizard_result_page, name="wizard_result"),
    path("wizard/checklist.pdf", wizard_pdf, name="wizard_pdf"),
    path("wizard/steps/", wizard_steps_page, name="wizard_steps"),
    path("dashboard/", dashboard_page, name="dashboard"),
    path("api/radar/", include("radar.urls")),
    path("dashboard/", dashboard_page, name="dashboard"),
    path("api/radar/", include("radar.urls")),
]

# ✅ Media files en dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
