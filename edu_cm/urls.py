from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from business import views as business_views
from billing import views_affiliate
from seo_agent import views as seo_views
import urllib.parse


def avatar_redirect(request):
    if settings.DEBUG:
        return redirect('http://127.0.0.1:8002/')
    return redirect('https://e-shelle.com/avatar/')



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
        from django.db.models import Q, Sum
        from business.models import BusinessCatalogItem, BusinessLeadEvent, BusinessProfile, HomeAdSlide
        now = timezone.now()
        premium_businesses = list(
            BusinessProfile.objects.filter(
                is_active=True,
                plan__in=[BusinessProfile.Plan.PREMIUM, BusinessProfile.Plan.BUSINESS],
            ).order_by("-boost_expires_at", "-subscription_expires_at", "-leads_count", "-updated_at")[:12]
        )
        recent_catalog_items = list(
            BusinessCatalogItem.objects.filter(is_active=True, business__is_active=True)
            .select_related("business")
            .order_by("-created_at")
        )
        try:
            from immobilier_cameroun.models import Bien, StatutBien
            recent_immo_items = list(
                Bien.objects.filter(statut=StatutBien.PUBLIE)
                .filter(Q(est_mis_en_avant=True) | Q(est_coup_de_coeur=True))
                .prefetch_related("photos")
                .order_by("-date_publication", "-updated_at")
            )
        except Exception:
            recent_immo_items = []
        premium_showcase_items = []
        for item in recent_catalog_items:
            business = item.business
            premium_showcase_items.append(
                {
                    "_rank": item.created_at,
                    "tag": item.get_item_type_display(),
                    "title": item.title,
                    "description": item.description,
                    "kind": f"{business.get_module_display()} · {business.city or 'Cameroun'}",
                    "meta": business.district or business.city or "Proche",
                    "price": item.price_label or "Prix a discuter",
                    "image": item.image_url,
                    "initial": item.title[:1],
                    "url": business.get_absolute_url(),
                    "contact_url": item.to_public_item().get("contact_url") or business.get_absolute_url(),
                    "views": business.views_count,
                    "leads": business.leads_count,
                }
            )
        for bien in recent_immo_items:
            photo = getattr(bien, "photo_principale", None)
            image = ""
            if photo and getattr(photo, "image", None):
                try:
                    image = photo.image.url
                except Exception:
                    image = ""
            try:
                contact_url = bien.get_whatsapp_url()
            except Exception:
                contact_url = bien.get_absolute_url()
            premium_showcase_items.append(
                {
                    "_rank": bien.date_publication or bien.updated_at,
                    "tag": "Immobilier",
                    "title": bien.titre,
                    "description": bien.description,
                    "kind": f"{bien.get_type_bien_display()} · {bien.ville}",
                    "meta": bien.quartier or bien.ville or "Cameroun",
                    "price": bien.prix_formate,
                    "image": image,
                    "initial": bien.titre[:1],
                    "url": bien.get_absolute_url(),
                    "contact_url": contact_url,
                    "views": bien.vues,
                    "leads": 0,
                }
            )
        premium_showcase_items = sorted(
            premium_showcase_items,
            key=lambda entry: entry.get("_rank") or now,
            reverse=True,
        )
        if len(premium_showcase_items) < 12:
            for business in premium_businesses:
                if len(premium_showcase_items) >= 12:
                    break
                premium_showcase_items.append(
                    {
                        "_rank": business.updated_at,
                        "tag": business.get_plan_display(),
                        "title": business.promo_headline or business.name,
                        "description": business.description,
                        "kind": f"{business.get_module_display()} · {business.city or 'Cameroun'}",
                        "meta": business.district or business.city or "Proche",
                        "price": "",
                        "image": business.promo_image.url if business.promo_image else "",
                        "initial": business.name[:1],
                        "url": business.get_absolute_url(),
                        "contact_url": business.promo_url or f"/chat/?q=Contacter%20{urllib.parse.quote(business.name)}",
                        "views": business.views_count,
                        "leads": business.leads_count,
                    }
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
        active_businesses = BusinessProfile.objects.filter(is_active=True)
        top_verified_businesses = list(
            active_businesses.filter(is_verified=True)
            .order_by("-leads_count", "-whatsapp_clicks", "-views_count", "-updated_at")[:6]
        )
        if len(top_verified_businesses) < 6:
            extra_ids = [business.pk for business in top_verified_businesses]
            top_verified_businesses += list(
                active_businesses.exclude(pk__in=extra_ids)
                .order_by("-leads_count", "-whatsapp_clicks", "-views_count", "-updated_at")[: 6 - len(top_verified_businesses)]
            )
        lead_total = active_businesses.aggregate(total=Sum("leads_count"))["total"] or 0
        whatsapp_total = active_businesses.aggregate(total=Sum("whatsapp_clicks"))["total"] or 0
        ctx["live_needs"] = [
            {"need": "Je cherche un restaurant ouvert a Makepe", "module": "Resto", "city": "Douala", "url": "/chat/?q=restaurant%20ouvert%20a%20Makepe"},
            {"need": "Je veux commander du gaz proche", "module": "Gaz", "city": "Bonamoussadi", "url": "/chat/?q=gaz%20proche%20Bonamoussadi"},
            {"need": "Je cherche un appartement a louer", "module": "Immobilier", "city": "Douala", "url": "/chat/?q=appartement%20a%20louer%20Douala"},
            {"need": "Je veux un pressing qui livre", "module": "Pressing", "city": "Yaounde", "url": "/chat/?q=pressing%20livraison%20Yaounde"},
        ]
        ctx["top_verified_businesses"] = top_verified_businesses
        ctx["home_numbers"] = {
            "businesses": active_businesses.count(),
            "premium": active_businesses.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]).count(),
            "products": BusinessCatalogItem.objects.filter(is_active=True, business__is_active=True).count(),
            "leads": lead_total + whatsapp_total,
            "ads": len(merged_slides),
            "events": BusinessLeadEvent.objects.count(),
        }
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        paginator = Paginator(premium_showcase_items, 30)
        page_num = request.GET.get('page', 1)
        try:
            paginated_items = paginator.page(page_num)
        except PageNotAnInteger:
            paginated_items = paginator.page(1)
        except EmptyPage:
            paginated_items = paginator.page(paginator.num_pages)

        ctx["premium_businesses"] = premium_businesses
        ctx["premium_showcase_items"] = paginated_items
        ctx["home_ad_slides"] = merged_slides[:10]
        ctx["hero_businesses"] = [item for item in premium_businesses if item.promo_image][:6] or premium_businesses[:6]
    except Exception:
        ctx["premium_businesses"] = []
        ctx["premium_showcase_items"] = []
        ctx["home_ad_slides"] = []
        ctx["hero_businesses"] = []
        ctx["live_needs"] = []
        ctx["top_verified_businesses"] = []
        ctx["home_numbers"] = {"businesses": 0, "premium": 0, "products": 0, "leads": 0, "ads": 0, "events": 0}
    return render(request, "home.html", ctx)


def presentation_view(request):
    ctx = {}
    try:
        from django.db.models import Sum
        from business.models import BusinessProfile, BusinessCatalogItem, BusinessLeadEvent, PresentationSlide
        active_businesses = BusinessProfile.objects.filter(is_active=True)
        lead_total = active_businesses.aggregate(total=Sum("leads_count"))["total"] or 0
        whatsapp_total = active_businesses.aggregate(total=Sum("whatsapp_clicks"))["total"] or 0
        ctx["home_numbers"] = {
            "businesses": active_businesses.count(),
            "premium": active_businesses.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]).count(),
            "products": BusinessCatalogItem.objects.filter(is_active=True, business__is_active=True).count(),
            "leads": lead_total + whatsapp_total,
            "events": BusinessLeadEvent.objects.count(),
        }
        ctx["slides"] = list(PresentationSlide.objects.filter(is_active=True).order_by("order", "-created_at"))
    except Exception:
        ctx["home_numbers"] = {"businesses": 0, "premium": 0, "products": 0, "leads": 0, "events": 0}
        ctx["slides"] = []
    return render(request, "presentation.html", ctx)


def tarifs_view(request):
    ctx = {}
    try:
        from django.db.models import Sum
        from business.models import BusinessProfile, ProviderPlan
        active_businesses = BusinessProfile.objects.filter(is_active=True)
        lead_total = active_businesses.aggregate(total=Sum("leads_count"))["total"] or 0
        whatsapp_total = active_businesses.aggregate(total=Sum("whatsapp_clicks"))["total"] or 0
        ctx["home_numbers"] = {
            "businesses": active_businesses.count(),
            "premium": active_businesses.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]).count(),
            "leads": lead_total + whatsapp_total,
        }
        ctx["plans"] = list(ProviderPlan.objects.filter(is_active=True).order_by("order", "monthly_price_xaf"))
    except Exception:
        ctx["home_numbers"] = {"businesses": 0, "premium": 0, "leads": 0}
        ctx["plans"] = []

    try:
        from business.views import BUSINESS_KEY_PRICE_XAF, BUSINESS_KEY_PARTNER_RECRUIT_RATE, BUSINESS_KEY_PROVIDER_RATE
        ctx["business_key_price"] = BUSINESS_KEY_PRICE_XAF
        ctx["partner_recruit_rate"] = BUSINESS_KEY_PARTNER_RECRUIT_RATE
        ctx["provider_rate"] = BUSINESS_KEY_PROVIDER_RATE
    except Exception:
        ctx["business_key_price"] = 9900
        ctx["partner_recruit_rate"] = 50
        ctx["provider_rate"] = 30

    return render(request, "tarifs.html", ctx)


def commercial_pdf_view(request):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return HttpResponse("ReportLab doit etre installe pour generer le PDF commercial.", status=500)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="E-Shelle-presentation-commerciale.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    navy = colors.HexColor("#07120D")
    green = colors.HexColor("#16A34A")
    gold = colors.HexColor("#FACC15")
    muted = colors.HexColor("#64748B")
    light = colors.HexColor("#F8FAFC")
    border = colors.HexColor("#D9E2EA")

    def money(value):
        return f"{value:,.0f} FCFA".replace(",", " ")

    def header(title, subtitle=None):
        pdf.setFillColor(navy)
        pdf.rect(0, height - 118, width, 118, stroke=0, fill=1)
        pdf.setFillColor(green)
        pdf.roundRect(42, height - 52, 88, 22, 7, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(55, height - 46, "E-SHELLE")
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawString(42, height - 82, title)
        if subtitle:
            pdf.setFont("Helvetica", 10)
            pdf.setFillColor(colors.Color(1, 1, 1, alpha=.72))
            pdf.drawString(42, height - 100, subtitle)

    def section_title(text, y):
        pdf.setFillColor(green)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(42, y, text)
        return y - 22

    def paragraph(text, x, y, max_chars=92, leading=14, color=muted):
        pdf.setFillColor(color)
        pdf.setFont("Helvetica", 9.5)
        words = text.split()
        line = ""
        for word in words:
            if len(line + " " + word) > max_chars:
                pdf.drawString(x, y, line.strip())
                y -= leading
                line = word
            else:
                line = f"{line} {word}"
        if line:
            pdf.drawString(x, y, line.strip())
            y -= leading
        return y

    def bullet(text, x, y):
        pdf.setFillColor(green)
        pdf.circle(x, y + 3, 2.4, stroke=0, fill=1)
        return paragraph(text, x + 12, y, max_chars=78, leading=13, color=colors.HexColor("#334155"))

    def card(x, y, w, h, title, body, accent=green):
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(border)
        pdf.roundRect(x, y - h, w, h, 10, stroke=1, fill=1)
        pdf.setFillColor(accent)
        pdf.roundRect(x + 14, y - 30, 28, 20, 6, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(x + 28, y - 24, "IA")
        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x + 50, y - 24, title)
        paragraph(body, x + 14, y - 50, max_chars=38, leading=12)

    header("Presentation commerciale", "Ecosysteme digital et IA pour business africains")
    y = height - 150
    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(42, y, "Digitalisez. Automatisez. Grandissez.")
    y -= 24
    y = paragraph(
        "E-Shelle est une plateforme modulaire qui aide les microfinances, cooperatives, agriculteurs, commercants, PME et organisations terrain a gerer leurs operations, vendre plus et produire des rapports fiables.",
        42,
        y,
        max_chars=88,
        leading=14,
    )
    y -= 12
    y = section_title("Modules prioritaires", y)
    card(42, y, 160, 102, "Tchaslucpay", "Collecte terrain, depots, CNI, recus PDF, anti-fraude, rapport agence.")
    card(218, y, 160, 102, "AgroConnect AI", "Marketplace agricole, prix du marche, assistant IA et dashboard producteur.", green)
    card(394, y, 160, 102, "Marketing IA", "Posts, publicites, calendrier editorial et messages WhatsApp prets a vendre.", gold)
    y -= 128
    y = section_title("Valeur pour le client", y)
    for item in [
        "Traçabilite des operations, clients, commandes, paiements et recus.",
        "Reduction des pertes grace aux alertes anti-fraude et rapports journaliers.",
        "Gain de temps avec des dashboards, exports PDF et notifications WhatsApp/SMS.",
        "Modules deployables separement ou comme ecosysteme complet.",
    ]:
        y = bullet(item, 48, y)
        y -= 3
    y -= 8
    y = section_title("Offres commerciales", y)
    offers = [("Starter", money(15000) + " / mois", "Page vitrine, catalogue simple, support WhatsApp."),
              ("Business", money(50000) + " / mois", "Dashboard, clients, commandes, rapports et notifications."),
              ("Pro IA", "Sur devis", "Agents IA, workflows metier, formation et deploiement personnalise.")]
    x = 42
    for title, price, desc in offers:
        pdf.setFillColor(light)
        pdf.setStrokeColor(border)
        pdf.roundRect(x, y - 96, 160, 96, 10, stroke=1, fill=1)
        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x + 14, y - 24, title)
        pdf.setFillColor(green)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x + 14, y - 44, price)
        paragraph(desc, x + 14, y - 62, max_chars=34, leading=11)
        x += 176

    pdf.showPage()
    header("Cas concret: Tchaslucpay", "Microfinance digitale, collecteurs, agence et clients")
    y = height - 150
    y = section_title("Ce que la demo montre", y)
    for item in [
        "Creation client avec numero CNI et date d'expiration.",
        "Depot terrain a partir de 500 XAF, retrait uniquement en agence.",
        "Reçu PDF, historique client et solde actualise.",
        "Agent anti-fraude, agent superviseur et coach collecteur.",
        "Rapport agence PDF et notifications WhatsApp/SMS preparees.",
    ]:
        y = bullet(item, 48, y)
        y -= 4
    y -= 8
    y = section_title("Script de vente en 20 secondes", y)
    y = paragraph(
        "E-Shelle n'est pas seulement une application. C'est un systeme digital complet qui transforme une activite locale en organisation moderne, suivie, traçable et capable de prendre de meilleures decisions grace a l'IA.",
        42,
        y,
        max_chars=88,
        leading=15,
        color=colors.HexColor("#334155"),
    )
    y -= 16
    y = section_title("Prochaine etape", y)
    for item in [
        "Programmer une demo de 10 minutes.",
        "Choisir le module prioritaire: Tchaslucpay, AgroConnect AI, Marketing IA ou Marketplace.",
        "Definir le pack et les adaptations metier.",
        "Former l'equipe et lancer un pilote terrain.",
    ]:
        y = bullet(item, 48, y)
        y -= 4

    pdf.setFillColor(navy)
    pdf.roundRect(42, 56, width - 84, 74, 12, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(62, 100, "Contact demo")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(62, 82, "WhatsApp: +237 680 625 082   |   E-Shelle par IMAGENAF")
    pdf.setFillColor(colors.Color(1, 1, 1, alpha=.65))
    pdf.drawString(62, 66, f"Document genere le {timezone.localdate().strftime('%d/%m/%Y')}")

    pdf.save()
    return response

urlpatterns = [
    path("avatar/", avatar_redirect, name="avatar_redirect"),
    path("e-shelle-commercial.pdf", commercial_pdf_view, name="commercial_pdf"),
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
    path("b/<slug:public_slug>/", business_views.public_profile, name="business_public_short"),
    path("ref/<str:ref_code>/", views_affiliate.ref_redirect, name="public_ref_redirect"),

    # ── Facebook Agent IA — Dashboard auto-publication ────────────────
    path("facebook-agent/", include("facebook_agent.urls", namespace="facebook_agent")),

    # ── WhatsApp Agent IA — Campagnes Meta WhatsApp Business ──────────
    path("whatsapp/", include("whatsapp_agent.urls", namespace="whatsapp_agent")),

    # ── Agent Commercial IA — Prospection & ventes prestataires ──────
    path("commercial-agent/", include("commercial_agent.urls", namespace="commercial_agent")),

    # ── Phone OCR Agent — Extraction locale de numeros depuis captures ─
    path("phone-ocr/", include("phone_ocr_agent.urls", namespace="phone_ocr_agent")),

    # ── SEO Agent IA — Audit & referencement naturel ────────────────
    path("seo/", include("seo_agent.urls", namespace="seo_agent")),
    path("robots.txt", seo_views.robots_txt, name="robots_txt"),
    path("sitemap.xml", seo_views.sitemap_xml, name="sitemap_xml"),

    # ── Audio Studio IA — voix-off et musiques pour video ───────────
    path("audio-studio/", include("audio_studio.urls", namespace="audio_studio")),

    # ── LEBELAGE Importer — test local et import Shopify ─────────────
    path("lebelage-importer/", include("lebelage_importer.urls", namespace="lebelage_importer")),

    # ── Shelle Premium — Formulaire public et dashboard staff ───────
    path("", include("shelle_premium.urls", namespace="shelle_premium")),

    # ── TIBO — Boutique dropshipping premium Canada ───────────────────
    path("tibo/", include("apps.tibo.urls", namespace="tibo")),
    path("api/tibo/", include("apps.tibo.api.urls", namespace="tibo_api")),

    # Page d'accueil
    path("", home_view, name="home"),
    path("presentation/", presentation_view, name="presentation"),
    path("tarifs/", tarifs_view, name="tarifs"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
