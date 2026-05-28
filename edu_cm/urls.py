from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import render
from billing import views_affiliate


def home_view(request):
    ctx = {}
    try:
        from gaz.models import DepotGaz
        ctx["gaz_depots_vedette"] = DepotGaz.objects.filter(
            is_active=True, abonnement_actif=True, is_featured=True
        ).select_related("ville", "quartier")[:3]
    except Exception:
        ctx["gaz_depots_vedette"] = []
    try:
        from django.utils import timezone
        from business.models import BusinessProfile, HomeAdSlide
        now = timezone.now()
        premium_businesses = list(
            BusinessProfile.objects.filter(
                is_active=True,
                plan__in=[BusinessProfile.Plan.PREMIUM, BusinessProfile.Plan.BUSINESS],
            ).order_by("-boost_expires_at", "-subscription_expires_at", "-leads_count", "-updated_at")[:12]
        )
        home_ad_slides = list(
            HomeAdSlide.objects.filter(is_active=True)
            .filter(starts_at__isnull=True)
            .exclude(ends_at__lt=now)
            .select_related("business")
            .order_by("order", "-created_at")[:12]
        )
        timed_slides = list(
            HomeAdSlide.objects.filter(is_active=True, starts_at__lte=now)
            .exclude(ends_at__lt=now)
            .select_related("business")
            .order_by("order", "-created_at")[:12]
        )
        slide_ids = set()
        merged_slides = []
        for slide in home_ad_slides + timed_slides:
            if slide.pk not in slide_ids and slide.is_live:
                merged_slides.append(slide)
                slide_ids.add(slide.pk)
        if merged_slides:
            from django.db.models import F
            HomeAdSlide.objects.filter(pk__in=[slide.pk for slide in merged_slides[:10]]).update(
                impressions_count=F("impressions_count") + 1
            )
        ctx["premium_businesses"] = premium_businesses
        ctx["home_ad_slides"] = merged_slides[:10]
        ctx["hero_businesses"] = [item for item in premium_businesses if item.promo_image][:6] or premium_businesses[:6]
    except Exception:
        ctx["premium_businesses"] = []
        ctx["home_ad_slides"] = []
        ctx["hero_businesses"] = []
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
    path("artisans/",    include("artisans.urls",    namespace="artisans")),
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
    path("chat/", include("chat.urls", namespace="chat")),
    path("business/", include("business.urls", namespace="business")),
    path("ref/<str:ref_code>/", views_affiliate.ref_redirect, name="public_ref_redirect"),

    # ── Facebook Agent IA — Dashboard auto-publication ────────────────
    path("facebook-agent/", include("facebook_agent.urls", namespace="facebook_agent")),

    # ── TIBO — Boutique dropshipping premium Canada ───────────────────
    path("tibo/", include("apps.tibo.urls", namespace="tibo")),
    path("api/tibo/", include("apps.tibo.api.urls", namespace="tibo_api")),

    # Page d'accueil
    path("", home_view, name="home"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
