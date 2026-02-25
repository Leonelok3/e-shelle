"""
Django settings – IMMIGRATION97
Production Ready – Secure – Optimized
⚠️ Aucun secret ne doit être commité
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _

# ======================================================
# BASE
# ======================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ======================================================
# SECURITY
# ======================================================

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY manquant dans .env")

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    "immigration97.com",
    "www.immigration97.com",
    "127.0.0.1",
    "localhost",
]

# ✅ OPTIM: permettre d'ajouter des hosts via .env sans casser la liste existante
# Ex: DJANGO_ALLOWED_HOSTS="api.immigration97.com,staging.immigration97.com"
_extra_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
if _extra_hosts:
    for h in [x.strip() for x in _extra_hosts.split(",") if x.strip()]:
        if h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)

CSRF_TRUSTED_ORIGINS = [
    "https://immigration97.com",
    "https://www.immigration97.com",
]

# ✅ OPTIM: idem pour CSRF via .env si besoin
# Ex: DJANGO_CSRF_TRUSTED_ORIGINS="https://staging.immigration97.com"
_extra_csrf = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
if _extra_csrf:
    for o in [x.strip() for x in _extra_csrf.split(",") if x.strip()]:
        if o not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(o)

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# ✅ IMPORTANT derrière Nginx/Proxy : permet à Django de reconnaître HTTPS via X-Forwarded-Proto
# Ne casse rien même si ce header n'est pas présent.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DEFAULT_DOMAIN = "immigration97.com"
DEFAULT_PROTOCOL = "https"

SITE_ID = 1

# ======================================================
# APPLICATIONS
# ======================================================

INSTALLED_APPS = [

    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Security / 2FA
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "two_factor",
    "axes",

    # Third-party
    "whitenoise.runserver_nostatic",
    "widget_tweaks",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "csp",

    # === TES APPS INTERNES ===
    "photos",
    "billing",
    "cv_generator",
    "authentification",
    "MotivationLetterApp",
    "eligibility",
    "core",
    "radar",
    "preparation_tests",
    "visaetude",
    "VisaTravailApp",
    "permanent_residence",
    "EnglishPrepApp.apps.EnglishprepappConfig",
    "GermanPrepApp.apps.GermanprepappConfig",
    "VisaTourismeApp",
    "DocumentsApp",
    "ai_engine",
    "actualite.apps.ActualiteConfig",
    "accounts.apps.AccountsConfig",
    "recruiters",
    "profiles",
    "legal",
    "italian_courses",
    "job_agent",
    "corsheaders",
    "mediafiles",
]

# ======================================================
# MIDDLEWARE
# ======================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ======================================================
# TEMPLATES  ✅ OBLIGATOIRE POUR ADMIN
# ======================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # obligatoire admin
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "billing.context_processors.premium_status",
            ],
        },
    },
]

# ======================================================
# DATABASE
# ======================================================

if os.environ.get("USE_POSTGRES", "True") == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME"),
            "USER": os.environ.get("DB_USER"),
            "PASSWORD": os.environ.get("DB_PASSWORD"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ======================================================
# INTERNATIONALISATION
# ======================================================

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("fr", _("Français")),
    ("en", _("English")),
    ("de", _("Deutsch")),
    ("it", _("Italiano")),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# ======================================================
# STATIC & MEDIA
# ======================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
PROTECTED_MEDIA_URL = "/protected-media/"
PROTECTED_MEDIA_ROOT = BASE_DIR / "media" / "protected-media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

MEDIA_URL = "/media/"
PROTECTED_MEDIA_URL = "/protected-media/"


# ✅ CRITIQUE (anti-perte en prod) :
# - Par défaut, on garde TON comportement actuel (BASE_DIR / "media") => zéro casse
# - En production, tu définis DJANGO_MEDIA_ROOT=/var/lib/immigration97/media (persistant sur VPS)
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

# ✅ Préparation "premium" pour médias protégés (audios premium/abonnement)
# Ne casse rien tant que tu ne l'utilises pas dans les URLs/Nginx.
PROTECTED_MEDIA_URL = "/protected-media/"
PROTECTED_MEDIA_ROOT = Path(
    os.environ.get("DJANGO_PROTECTED_MEDIA_ROOT", "/var/lib/immigration97/protected-media")
)

# ✅ Durcissement des fichiers uploadés (permissions Linux)
# 0o640 = propriétaire rw, groupe r, autres rien.
FILE_UPLOAD_PERMISSIONS = 0o640

# ✅ Limites raisonnables (évite abus) — à ajuster si besoin (PDF, audio longs, etc.)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE", str(25 * 1024 * 1024)))  # 25MB
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024)))  # 10MB

# ======================================================
# EMAIL – HOSTINGER
# ======================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.hostinger.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "Immigration97 <contact@immigration97.com>"
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_TIMEOUT = 10

# ======================================================
# AUTH
# ======================================================

# AUTH
LOGIN_URL = "authentification:login"

# ✅ Après connexion -> Mon espace (dashboard)
LOGIN_REDIRECT_URL = "/profiles/"   # ou ton URL exacte dashboard

# ✅ Après logout -> Accueil
LOGOUT_REDIRECT_URL = "home"


AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_LOCK_OUT_AT_FAILURE = True
AXES_COOLOFF_TIME = 1

# ======================================================
# CSP
# ======================================================
# Nouvelle configuration django-csp 4.0+
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ("'self'",),
        'connect-src': ("'self'",),
        'font-src': ("'self'", 'https://fonts.gstatic.com', 'data:'),
        'frame-src': ("'self'",),
        'img-src': ("'self'", 'data:', 'https://res.cloudinary.com'),
        'script-src': ("'self'", 'https://cdnjs.cloudflare.com', "'unsafe-inline'"),
        'style-src': ("'self'", 'https://fonts.googleapis.com', "'unsafe-inline'"),
    }
}
# ======================================================
# LOGGING
# ======================================================

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "django-error.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = [
    "https://fr.indeed.com",
    "https://www.indeed.com",
    "https://immigration97.com",
    "https://www.immigration97.com",
]
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

CORS_ALLOW_CREDENTIALS = True


# ======================================================
# Cookies cross-site (sinon Indeed -> API n'envoie pas la session)
# ======================================================
if DEBUG:
    # ✅ Localhost (HTTP) -> cookies acceptés
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    # ✅ Production (HTTPS) -> cross-site OK
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True

# ✅ Petit durcissement CSRF (ne casse pas)
CSRF_COOKIE_HTTPONLY = True

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^chrome-extension://.*$",
]



# ...existing code...

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # ...existing code...
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Immigration97 API",
    "DESCRIPTION": "API documentation",
    "VERSION": "1.0.0",
}

# ...existing code...


# ...existing code...
import os

DEBUG = os.getenv("DJANGO_DEBUG", "False").strip().lower() in ("1", "true", "yes")

SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True" if not DEBUG else "False").strip().lower() in ("1", "true", "yes")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True" if not DEBUG else "False").strip().lower() in ("1", "true", "yes")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True" if not DEBUG else "False").strip().lower() in ("1", "true", "yes")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # ...existing code...
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Immigration97 API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "API documentation",
    "DISABLE_ERRORS_AND_WARNINGS": True,  # supprime W002 drf_spectacular
}
# ...existing code...