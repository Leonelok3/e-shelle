"""
Django settings (durdi) pour immigration97.
NE PAS committer de secrets — utiliser .env exclusivement.
"""

from pathlib import Path
import os
from django.utils.translation import gettext_lazy as _

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Charger .env (pour le dev)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# ======================================================
# 🔐 SÉCURITÉ — OBLIGATOIREMENT VIA ENV
# ======================================================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "replace-me-locally")
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

# Forcer la désactivation de HTTPS en mode DEBUG
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

ALLOWED_HOSTS = [
    "immigration97.com",
    "www.immigration97.com",
    "127.0.0.1",
    "localhost",
]





CSRF_TRUSTED_ORIGINS = [
    "http://31.97.196.197:8000",
    "http://31.97.196.197",
]


# API Keys

GOOGLE_GENAI_API_KEY = os.environ.get("GOOGLE_GENAI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")



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

    # 2FA & OTP
    "two_factor",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",

    # Third-party
    "whitenoise.runserver_nostatic",
    "django_extensions",
    "widget_tweaks",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "csp",
    "axes",

    # Internal apps
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
    "profiles",
]

# ======================================================
# MIDDLEWARE
# ======================================================
MIDDLEWARE = [
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
# TEMPLATES
# ======================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
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
# DATABASE (CORRIGÉ)
# ======================================================
if os.environ.get("USE_POSTGRES", "False") == "True":
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
LANGUAGES = [("fr", _("Français")), ("en", _("Anglais"))]
LOCALE_PATHS = [BASE_DIR / "locale"]

# ======================================================
# STATIC & MEDIA
# ======================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

if DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ======================================================
# AUTHENTIFICATION
# ======================================================
# ======================================================
# AUTHENTIFICATION (CORRIGÉ & PRO)
# ======================================================
SITE_ID = 1

LOGIN_URL = "authentification:login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ======================================================
# SECURITY HEADERS
# ======================================================
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False") == "True"

if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SECURE_HSTS_SECONDS = 0

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ======================================================
# CSP
# ======================================================
if DEBUG:
    CONTENT_SECURITY_POLICY = {
        "DIRECTIVES": {
            "default-src": ("'self'",),
            "script-src": ("'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com"),
            "style-src": ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com"),
            "img-src": ("'self'", "data:", "https://res.cloudinary.com"),
            "font-src": ("'self'", "https://fonts.gstatic.com"),
        }
    }
else:
    CONTENT_SECURITY_POLICY = {
        "DIRECTIVES": {
            "default-src": ("'self'",),
            "script-src": ("'self'", "https://cdnjs.cloudflare.com"),
            "style-src": ("'self'", "https://fonts.googleapis.com"),
            "img-src": ("'self'", "data:", "https://res.cloudinary.com"),
            "font-src": ("'self'", "https://fonts.gstatic.com"),
        }
    }

# ======================================================
# EMAIL
# ======================================================
# ======================================================
# EMAIL CONFIG – HOSTINGER (PRODUCTION READY)
# ======================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.hostinger.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))

# 🔐 Sécurité SMTP Hostinger
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = False  # ⚠️ NE PAS UTILISER SSL AVEC 587

EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "contact@immigration97.com")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "Immigration97 <contact@immigration97.com>"
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_TIMEOUT = 10


# ======================================================
# LOGGING
# ======================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": str(BASE_DIR / "logs" / "django-error.log"),
        },
    },
    "loggers": {"django": {"handlers": ["file"], "level": "ERROR", "propagate": True}},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ======================================================
# SITE & DOMAIN (OBLIGATOIRE POUR EMAILS)
# ======================================================

SITE_ID = 1

DEFAULT_DOMAIN = "immigration97.com"
DEFAULT_PROTOCOL = "https"


# Utilisé par PasswordResetView
EMAIL_USE_LOCALTIME = True

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_LOCK_OUT_AT_FAILURE = True
AXES_RESET_ON_SUCCESS = True
AXES_COOLOFF_TIME = 1  # 1 heure
AXES_LOCKOUT_TEMPLATE = None
AXES_LOCKOUT_URL = None


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",
    },
}


DEFAULT_CHARSET = "utf-8"

FILE_CHARSET = "utf-8"

#LANGUAGE_CODE = "fr"
USE_I18N = True
USE_L10N = True
