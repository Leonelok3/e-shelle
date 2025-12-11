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

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_GENAI_API_KEY = os.environ.get("GOOGLE_GENAI_API_KEY", "")

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
    "csp",          # Content Security Policy
    "axes",         # Bruteforce protection

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
    "csp.middleware.CSPMiddleware",  # CSP first
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",  # 2FA
    "axes.middleware.AxesMiddleware",       # Bruteforce protection
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
            ],
        },
    },
]

# ======================================================
# ======================================================
# DATABASE
# ======================================================
# The settings prefer a DATABASE_URL env var (good for prod). If not present,
# check USE_POSTGRES to enable the explicit postgres config. Otherwise fall back
# ======================================================
# DATABASE
# ======================================================
if os.environ.get("USE_POSTGRES", "False") == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "immigration97_db",
            "USER": "immigration97_user",  # ← REMETTRE ICI
            "PASSWORD": "Dodipro1207.",
            "HOST": "localhost",
            "PORT": "5433",
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

# Utiliser le storage approprié selon l'environnement
if DEBUG:
    # En développement : pas de compression/hashing pour faciliter le debug
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    # En production : compression et hashing des fichiers
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ======================================================
# AUTHENTIFICATION
# ======================================================
SITE_ID = 1
LOGIN_URL = os.environ.get("LOGIN_URL", "/authentification/login")
LOGIN_REDIRECT_URL = os.environ.get("LOGIN_REDIRECT_URL", "/cv-generator/cv/list/")
LOGOUT_REDIRECT_URL = "/"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ======================================================
# SECURITY HEADERS (Adaptés pour dev/prod)
# ======================================================
# Les cookies sécurisés sont désactivés en mode DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

# SSL Redirect désactivé par défaut (activer en prod via .env)
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False") == "True"

# HSTS uniquement en production
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
# CSP (Content Security Policy)
# ======================================================
# En mode DEBUG, on assouplit CSP pour faciliter le développement
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
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.hostinger.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "465"))
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "True") == "True"
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@immigration97.com")

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