from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Sécurité
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,e-shelle.com,www.e-shelle.com"
).split(",") if h.strip()]
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

DEFAULT_CSRF_ORIGINS = [
    "https://e-shelle.com",
    "https://www.e-shelle.com",
]
DEFAULT_CSRF_ORIGINS += [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        os.getenv("MAPEX_CSRF_TRUSTED_ORIGINS", "https://mapex.e-shelle.com")
    ).split(",")
    if origin.strip()
]
DEFAULT_CSRF_ORIGINS += [
    origin.strip()
    for origin in os.getenv("ESHELLE_SUBDOMAIN_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if RENDER_EXTERNAL_HOSTNAME:
    DEFAULT_CSRF_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
if RAILWAY_PUBLIC_DOMAIN:
    DEFAULT_CSRF_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")
DEFAULT_CSRF_ORIGINS += [
    origin.strip()
    for origin in os.getenv(
        "RAILWAY_CSRF_TRUSTED_ORIGINS",
        "https://*.up.railway.app"
    ).split(",")
    if origin.strip()
]
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(DEFAULT_CSRF_ORIGINS))

# Headers / cookies de sécurité communs
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

# Apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework.authtoken",

    "accounts.apps.AccountsConfig",
    "curriculum.apps.CurriculumConfig",
    "content.apps.ContentConfig",
    "progress.apps.ProgressConfig",
    "api.apps.ApiConfig",

    # Modules E-Shelle SaaS
    "formations.apps.FormationsConfig",
    "boutique.apps.BoutiqueConfig",
    "services.apps.ServicesConfig",
    "artisans.apps.ArtisansConfig",
    "dashboard.apps.DashboardConfig",
    "ai_engine.apps.AiEngineConfig",
    "payments.apps.PaymentsConfig",

    # Abonnements / paiements avancés
    "billing.apps.BillingConfig",

    # MathCM — Mathématiques secondaire MINESEC
    "math_cm.apps.MathCmConfig",

    # Cours de langues (immigration97)
    "EnglishPrepApp.apps.EnglishprepappConfig",
    "GermanPrepApp.apps.GermanprepappConfig",
    "italian_courses.apps.ItalianCoursesConfig",
    "preparation_tests.apps.PreparationTestsConfig",
    "immobilier_cameroun.apps.ImmobilierCamerounConfig",
    "auto_cameroun.apps.AutoCamerounConfig",
    "annonces_cam.apps.AnnoncesCamConfig",

    # Sites framework (utilisé pour les URLs absolues de partage)
    "django.contrib.sites",

    # ── E-Shelle Love — Application de rencontres ──────────────────
    "rencontres.apps.RencontresConfig",

    # ── E-Shelle Agro — Marketplace Agroalimentaire Africaine ───────
    "agro.apps.AgroConfig",

    # ── EduCam Pro — Plateforme E-Learning ───────────────────────
    "edu_platform.apps.EduPlatformConfig",

    # ── E-Shelle Resto — Découverte de restaurants au Cameroun ───
    "resto.apps.RestoConfig",

    # ── Njangi Digital — Tontine & Fond commun numérique ──────────
    "njangi.apps.NjangiConfig",

    # ── AdGen — Générateur de publicités IA ───────────────────────
    "adgen.apps.AdgenConfig",

    # ── E-Shelle Gaz — Livraison de gaz domestique ────────────────
    "gaz.apps.GazConfig",

    # ── E-Shelle Pharma — Annuaire pharmacies & médicaments ───────
    "pharma.apps.PharmaConfig",

    # ── E-Shelle Pressing — Pressing & Blanchisserie ──────────────
    "pressing.apps.PressingConfig",

    # ── E-Shelle Jobs — Emplois, stages & missions ───────────────
    "jobs.apps.JobsConfig",

    # ── E-Shelle Transport — Covoiturage & trajets interurbains ───
    "transport_core.apps.TransportCoreConfig",

    # ── E-Shelle Santé — Produits santé & professionnels ──────────
    "sante.apps.SanteConfig",

    # ── E-Shelle AI — Agent Intelligent Central ────────────────────
    "e_shelle_ai.apps.EshelleAiConfig",
    "chat.apps.ChatConfig",
    "business.apps.BusinessConfig",

    # ── Facebook Agent IA — Auto-publication sur la page Facebook ──
    "facebook_agent.apps.FacebookAgentConfig",

    # ── WhatsApp Agent IA — Campagnes Meta WhatsApp Business ───────
    "whatsapp_agent.apps.WhatsappAgentConfig",

    # ── Agent Commercial IA — Pipeline ventes E-Shelle ─────────────
    "commercial_agent.apps.CommercialAgentConfig",

    # ── Phone OCR Agent — Extraction locale de numeros depuis images ─
    "phone_ocr_agent.apps.PhoneOcrAgentConfig",

    # ── SEO Agent IA — Audit, GEO, schema, CTA et indexation Google ─
    "seo_agent.apps.SeoAgentConfig",

    # ── Audio Studio IA — Voix-off, voix enregistrees et musiques video ─
    "audio_studio.apps.AudioStudioConfig",

    # ── LEBELAGE Importer — Scraping produit vers Shopify ───────────
    "lebelage_importer.apps.LebelageImporterConfig",

    # ── Shelle Premium — Cartes prestataires autonomes ─────────────
    "shelle_premium.apps.ShellePremiumConfig",

    # ── TIBO — Dropshipping premium Canada ────────────────────────
    "apps.tibo.apps.TiboConfig",

    # ── Celery Beat — Scheduler persistant en base ──────────────────
    "django_celery_beat",
    "django_celery_results",

    # ── Social Auth (Google, Facebook) ─────────────────────────────
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",

    # ── E-Shelle Allemagne — Immigrations / Ausbildung / Lebenslauf ─
    "germany_opportunities.apps.GermanyOpportunitiesConfig",
    "lebenslauf.apps.LebenslaufConfig",
]

# ── E-Shelle AI — Configuration ─────────────────────────────────────
OPENAI_CHAT_MODEL         = "gpt-4o"
OPENAI_IMAGE_MODEL        = "dall-e-3"
OPENAI_IMAGE_SIZE         = "1024x1024"
OPENAI_IMAGE_QUALITY      = "hd"
AI_MAX_CONTEXT_MESSAGES   = 20   # Nb messages gardés dans le contexte GPT
AI_MEMORY_SUMMARY_THRESHOLD = 40 # Résumé auto après N messages

# AdGen
ADGEN_MAX_CAMPAIGNS_FREE = 5
ADGEN_MAX_TOKENS_FREE    = 50000

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # ── EduCam Pro : verrouillage appareil (/edu/ uniquement) ────
    "edu_platform.middleware.device_lock_middleware.DeviceLockMiddleware",

    # ── Allauth (social login) ────────────────────────────────────
    "allauth.account.middleware.AccountMiddleware",
    "apps.tibo.middleware.security.TiboSecurityHeadersMiddleware",
]

ROOT_URLCONF = "edu_cm.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.media",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.eshelle_public_urls",
                # ── E-Shelle Resto ────────────────────────────────────
                "resto.context_processors.resto_globals",
                # ── Abonnements globaux (injecte user_subs dans tous les templates)
                "accounts.context_processors.subscription_context",
                "accounts.context_processors.social_login_context",
                # allauth context processor — non requis pour social login
            ],
        },
    },
]

WSGI_APPLICATION = "edu_cm.wsgi.application"

# Base de données — SQLite en dev, PostgreSQL en prod (via DATABASE_URL)
USE_SQLITE = os.getenv("USE_SQLITE", "").lower() in ("1", "true", "yes")
USE_POSTGRES = os.getenv("USE_POSTGRES", "").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL and not USE_SQLITE and (not DEBUG or USE_POSTGRES == "true"):
    import urllib.parse as _up
    _u = _up.urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE":   "django.db.backends.postgresql",
            "NAME":     _u.path.lstrip("/"),
            "USER":     _u.username,
            "PASSWORD": _u.password,
            "HOST":     _u.hostname,
            "PORT":     str(_u.port or 5432),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Mot de passe
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Langue / Heure
LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

# Static / Media
STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ✅ Custom User (IMPORTANT)
AUTH_USER_MODEL = "accounts.CustomUser"

# Auth redirects
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "accounts:login"

# ── Backends d'authentification ───────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ── django-allauth configuration ──────────────────────────────────────
ACCOUNT_ADAPTER          = "accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER    = "accounts.adapters.SocialAccountAdapter"

# Connexion par email ou username
ACCOUNT_LOGIN_METHODS      = {"username", "email"}
ACCOUNT_EMAIL_VERIFICATION = "none"       # pas de vérif email via allauth (on gère)
# Champs requis à l'inscription (format allauth 65+)
ACCOUNT_SIGNUP_FIELDS      = ["email*", "password1*", "password2*"]

# Social signup automatique — pas de page intermédiaire
SOCIALACCOUNT_AUTO_SIGNUP       = True
SOCIALACCOUNT_LOGIN_ON_GET      = True    # démarre OAuth sur clic direct
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # fusionne si email connu

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "FETCH_USERINFO": True,
    },
    "facebook": {
        "METHOD": "oauth2",
        "SCOPE": ["email", "public_profile"],
        "FIELDS": ["id", "email", "name", "first_name", "last_name", "picture"],
        "EXCHANGE_TOKEN": True,
        "VERSION": "v18.0",
    },
}

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["google"]["APP"] = {
        "client_id": GOOGLE_CLIENT_ID,
        "secret": GOOGLE_CLIENT_SECRET,
        "key": ""
    }

if FACEBOOK_APP_ID and FACEBOOK_APP_SECRET and FACEBOOK_APP_ID != "VOTRE_APP_ID_ICI":
    SOCIALACCOUNT_PROVIDERS["facebook"]["APP"] = {
        "client_id": FACEBOOK_APP_ID,
        "secret": FACEBOOK_APP_SECRET,
        "key": ""
    }


# Anthropic / Claude AI
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# OpenAI (EnglishPrepApp, GermanPrepApp, italian_courses)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Google GenAI / Vertex AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_VIDEO_MODEL = os.getenv("GOOGLE_VIDEO_MODEL", "veo-2.0-generate-001")
GCP_VERTEX_KEY_PATH = os.getenv("GCP_VERTEX_KEY_PATH", str(BASE_DIR / "gcp_vertex_key.json"))


# Email (dev : console, prod : SMTP)
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST     = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT     = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS  = True
EMAIL_HOST_USER     = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL  = os.getenv("DEFAULT_FROM_EMAIL", "noreply@e-shelle.com")

# Sécurité HTTPS (activée quand DEBUG=False)
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() == "true"
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() == "true"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "63072000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_REDIRECT_EXEMPT = os.getenv("SECURE_REDIRECT_EXEMPT", "").split(",") if os.getenv("SECURE_REDIRECT_EXEMPT") else []

# Taille max upload (fichiers produits digitaux)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800   # 50 Mo
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800   # 50 Mo

# ── Immobilier Cameroun ─────────────────────────────────────────
IMMOBILIER_MAX_PHOTOS_PAR_BIEN  = 10
IMMOBILIER_MAX_BIENS_GRATUIT    = 3
IMMOBILIER_TAILLE_MAX_IMAGE_MB  = 5
IMMO_WHATSAPP_CONTACT           = "+237680625082"

# ── Auto Cameroun ────────────────────────────────────────────────
AUTO_MAX_VEHICULES_GRATUIT  = 3
AUTO_TAILLE_MAX_IMAGE_MB    = 5
AUTO_WHATSAPP_CONTACT       = "+237680625082"

# DRF
# ── Rencontres ────────────────────────────────────────────────────
RENCONTRES_SETTINGS = {
    'MAX_PHOTOS_FREE': 6,
    'MAX_PHOTOS_PREMIUM': 12,
    'LIKES_PAR_JOUR_FREE': 5,
    'SUPER_LIKES_PAR_JOUR_FREE': 1,
    'MESSAGES_PAR_JOUR_FREE': 5,
    'AGE_MINIMUM': 18,
    'BOOST_DUREE_MINUTES': 30,
}

# ── E-Shelle Agro ────────────────────────────────────────────────
AGRO_SETTINGS = {
    'PRODUITS_PAR_PAGE':        24,
    'PHOTOS_MAX_PAR_PRODUIT':   8,
    'TAILLE_MAX_PHOTO_MB':      5,
    'MODERATION_AUTO':          False,   # True = publication directe sans validation
    'DEVISE_DEFAUT':            'XAF',
    'PAYS_DEFAUT':              'CM',
    'LANGUES_SUPPORTEES':       ['fr', 'en', 'pt', 'es', 'ar'],
    'WHATSAPP_SUPPORT':         '+237680625082',
}

# ── EduCam Pro ────────────────────────────────────────────────────
EDU_PLATFORM = {
    'SITE_NAME': 'EduCam Pro',
    'CURRENCY': 'XAF',
    'ORANGE_MONEY_API_KEY':      os.getenv('ORANGE_MONEY_API_KEY', ''),
    'ORANGE_MONEY_API_SECRET':   os.getenv('ORANGE_MONEY_API_SECRET', ''),
    'ORANGE_MONEY_MERCHANT_KEY': os.getenv('ORANGE_MONEY_MERCHANT_KEY', ''),
    'MTN_MOMO_SUBSCRIPTION_KEY': os.getenv('MTN_MOMO_SUBSCRIPTION_KEY', ''),
    'MTN_MOMO_API_USER':         os.getenv('MTN_MOMO_API_USER', ''),
    'MTN_MOMO_API_KEY':          os.getenv('MTN_MOMO_API_KEY', ''),
    'MTN_MOMO_ENVIRONMENT':      os.getenv('MTN_MOMO_ENVIRONMENT', 'sandbox'),
    'WEBHOOK_HMAC_SECRET':       os.getenv('EDU_WEBHOOK_HMAC_SECRET', ''),
    'MAX_DEVICES_PER_CODE': 1,
    'SMS_PROVIDER': os.getenv('SMS_PROVIDER', 'twilio'),
    'SEND_CODE_BY_EMAIL': True,
    'SEND_CODE_BY_SMS': True,
}

# URL de base pour les webhooks Mobile Money
SITE_URL = os.getenv('SITE_URL', 'https://e-shelle.com')
FORMATIONS_PUBLIC_URL = os.getenv("FORMATIONS_PUBLIC_URL", "/formations/")
BOUTIQUE_PUBLIC_URL = os.getenv("BOUTIQUE_PUBLIC_URL", "/boutique/")
SERVICES_PUBLIC_URL = os.getenv("SERVICES_PUBLIC_URL", "/services/")
MATHS_PUBLIC_URL = os.getenv("MATHS_PUBLIC_URL", "/maths/")
LANGUES_PUBLIC_URL = os.getenv("LANGUES_PUBLIC_URL", "/langues/")
ANGLAIS_PUBLIC_URL = os.getenv("ANGLAIS_PUBLIC_URL", "/anglais/")
ALLEMAND_PUBLIC_URL = os.getenv("ALLEMAND_PUBLIC_URL", "/allemand/")
ITALIEN_PUBLIC_URL = os.getenv("ITALIEN_PUBLIC_URL", "/italien/")
PREP_PUBLIC_URL = os.getenv("PREP_PUBLIC_URL", "/prep/")
IMMOBILIER_PUBLIC_URL = os.getenv("IMMOBILIER_PUBLIC_URL", "/immobilier/")
AUTO_PUBLIC_URL = os.getenv("AUTO_PUBLIC_URL", "/auto/")
ANNONCES_PUBLIC_URL = os.getenv("ANNONCES_PUBLIC_URL", "/annonces/")
MARKET_PUBLIC_URL = os.getenv("MARKET_PUBLIC_URL", ANNONCES_PUBLIC_URL)
LOVE_PUBLIC_URL = os.getenv("LOVE_PUBLIC_URL", "/rencontres/")
AGRO_PUBLIC_URL = os.getenv("AGRO_PUBLIC_URL", "/agro/")
RESTO_PUBLIC_URL = os.getenv("RESTO_PUBLIC_URL", "/resto/")
NJANGI_PUBLIC_URL = os.getenv("NJANGI_PUBLIC_URL", "/njangi/")
ADGEN_PUBLIC_URL = os.getenv("ADGEN_PUBLIC_URL", "/pub/")
GAZ_PUBLIC_URL = os.getenv("GAZ_PUBLIC_URL", "/gaz/")
PHARMA_PUBLIC_URL = os.getenv("PHARMA_PUBLIC_URL", "/pharma/")
PRESSING_PUBLIC_URL = os.getenv("PRESSING_PUBLIC_URL", "/pressing/")
AI_PUBLIC_URL = os.getenv("AI_PUBLIC_URL", "/ai/")
JOBS_PUBLIC_URL = os.getenv("JOBS_PUBLIC_URL", "/jobs/")
TRANSPORT_PUBLIC_URL = os.getenv("TRANSPORT_PUBLIC_URL", "/transport/")
SANTE_PUBLIC_URL = os.getenv("SANTE_PUBLIC_URL", "/sante/")
TCHASLUCPAY_PUBLIC_URL = os.getenv("TCHASLUCPAY_PUBLIC_URL", "http://127.0.0.1:8001/")
SIMPLO_PUBLIC_URL = os.getenv("SIMPLO_PUBLIC_URL", "http://127.0.0.1:8020/")
MAPEX_PUBLIC_URL = os.getenv("MAPEX_PUBLIC_URL", "http://127.0.0.1:8000/edu/")
EXPROD_PUBLIC_URL = os.getenv("EXPROD_PUBLIC_URL", "/lebelage-importer/")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# ── E-Shelle Resto ────────────────────────────────────────────────
RESTO_FREE_TRIAL_DAYS = 30

# ── Facebook Agent IA ─────────────────────────────────────────────
FACEBOOK_APP_ID     = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")

# ── WhatsApp Agent IA — Meta WhatsApp Business API ────────────────
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_API_URL = os.getenv(
    "WHATSAPP_API_URL",
    f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages",
)
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_DRY_RUN = os.getenv("WHATSAPP_DRY_RUN", "True").lower() in ("1", "true", "yes")
WHATSAPP_CONFIG_READY = bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID and WHATSAPP_VERIFY_TOKEN)

# ── Celery — Broker & Backend ──────────────────────────────────────
CELERY_BROKER_URL         = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND     = "django-db"          # stockage résultats en base Django
CELERY_CACHE_BACKEND      = "default"
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TASK_SERIALIZER    = "json"
CELERY_RESULT_SERIALIZER  = "json"
CELERY_TIMEZONE           = TIME_ZONE
CELERY_BEAT_SCHEDULER     = "django_celery_beat.schedulers:DatabaseScheduler"

# Celery Beat — planning défini dans edu_cm/celery.py (app.conf.beat_schedule)

# ── Logging — capture les erreurs Django en production ─────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "django_errors": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": os.getenv("DJANGO_LOG_FILE", "/tmp/django_errors.log"),
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["django_errors", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["django_errors", "console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

