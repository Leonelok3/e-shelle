from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import render


def home_view(request):
    ctx = {}
    try:
        from gaz.models import DepotGaz
        ctx["gaz_depots_vedette"] = DepotGaz.objects.filter(
            is_active=True, abonnement_actif=True, is_featured=True
        ).select_related("ville", "quartier")[:3]
    except Exception:
        ctx["gaz_depots_vedette"] = []
    return render(request, "home.html", ctx)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentification (vues custom E-Shelle)
    path("accounts/", include("accounts.urls")),
    # Allauth account URLs (account_inactive, etc.)
    path("accounts/", include("allauth.account.urls")),
    # Social Auth — URLs de base (connections, disconnect, signup)
    path("accounts/social/", include("allauth.socialaccount.urls")),
    # Social Auth — OAuth2 Google : google/ est déjà dans le module
    path("accounts/social/", include("allauth.socialaccount.providers.google.urls")),
    # Social Auth — OAuth2 Facebook : facebook/ est déjà dans le module
    path("accounts/social/", include("allauth.socialaccount.providers.facebook.urls")),

    # Anciens dashboards (compatibilité)
    path("dash/", include("progress.urls")),

    # Modules E-Shelle SaaS
    path("formations/",  include("formations.urls",  namespace="formations")),
    path("boutique/",    include("boutique.urls",    namespace="boutique")),
    path("services/",    include("services.urls",    namespace="services")),
    path("dashboard/",   include("dashboard.urls",   namespace="dashboard")),
    path("payments/",    include("payments.urls",    namespace="payments")),
    path("ia/",          include("ai_engine.urls",   namespace="ai_engine")),

    # API REST
    path("api/v1/",      include("api.urls",         namespace="api")),

    # Abonnements
    path("billing/",     include("billing.urls",         namespace="billing")),

    # MathCM — Mathématiques secondaire MINESEC
    path("maths/", include("math_cm.urls", namespace="math_cm")),

    # Hub des langues
    path("langues/", TemplateView.as_view(template_name="langues/hub.html"), name="langues_hub"),

    # Cours de langues
    path("anglais/",     include("EnglishPrepApp.urls",    namespace="englishprep")),
    path("allemand/",    include("GermanPrepApp.urls",     namespace="germanprep")),
    path("italien/",     include("italian_courses.urls",   namespace="italian_courses")),
    path("prep/",        include("preparation_tests.urls", namespace="preparation_tests")),

    # Immobilier Cameroun
    path("immobilier/", include("immobilier_cameroun.urls", namespace="immobilier")),

    # Auto Cameroun
    path("auto/", include("auto_cameroun.urls", namespace="auto")),

    # Annonces Cam (marketplace généraliste)
    path("annonces/", include("annonces_cam.urls", namespace="annonces")),

    # ── E-Shelle Love — Rencontres ────────────────────────────────
    path("rencontres/", include("rencontres.urls", namespace="rencontres")),

    # ── E-Shelle Agro — Marketplace Agroalimentaire Africaine ────────
    path("agro/", include("agro.urls", namespace="agro")),

    # ── EduCam Pro — Plateforme E-Learning ───────────────────────────
    path("edu/", include("edu_platform.urls", namespace="edu")),

    # ── E-Shelle Resto — Découverte de restaurants au Cameroun ───────
    path("resto/", include("resto.urls", namespace="resto")),

    # ── Njangi Digital — Tontine & Fond commun numérique ─────────────
    path("njangi/", include("njangi.urls", namespace="njangi")),

    # ── AdGen — Générateur de publicités IA ──────────────────────────
    path("pub/", include("adgen.urls", namespace="adgen")),

    # ── E-Shelle Gaz — Livraison de gaz domestique ───────────────────
    path("gaz/", include("gaz.urls", namespace="gaz")),

    # ── E-Shelle Pharma — Annuaire pharmacies & médicaments ─────────
    path("pharma/", include("pharma.urls", namespace="pharma")),

    # ── E-Shelle Pressing — Pressing & Blanchisserie ─────────────────
    path("pressing/", include("pressing.urls", namespace="pressing")),

    # ── E-Shelle Jobs — Emplois, stages & missions ───────────────────
    path("jobs/", include("jobs.urls", namespace="jobs")),

    # ── E-Shelle Transport — Covoiturage & trajets interurbains ───────
    path("transport/", include("transport_core.urls", namespace="transport")),

    # ── E-Shelle Santé — Produits santé & professionnels ──────────────
    path("sante/", include("sante.urls", namespace="sante")),

    # ── E-Shelle AI — Agent Intelligent Central ───────────────────────
    path("ai/", include("e_shelle_ai.urls", namespace="eshelle_ai")),

    # ── Facebook Agent IA — Dashboard auto-publication ────────────────
    path("facebook-agent/", include("facebook_agent.urls", namespace="facebook_agent")),

    # Page d'accueil
    path("", home_view, name="home"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
