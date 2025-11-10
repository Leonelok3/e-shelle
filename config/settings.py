"""
Fichier de configuration Django du projet immigration97.
Ici, on ajoute l'app 'preparation_tests', et on configure les répertoires
de templates et de fichiers statiques (CSS/JS).
"""

from pathlib import Path
import os
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

load_dotenv()

# === CONFIG GÉNÉRALE ===
BASE_DIR = Path(__file__).resolve().parent.parent

# Clé OpenAI (ACTION: Désactivée pour forcer le mode Démo/Fallback)
OPENAI_API_KEY = ""
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ⚠️ Secret key: ne pas commiter en prod (utiliser les variables d'environnement)
SECRET_KEY = "django-insecure-r-#hl^4p=7e5)hwqn#moz4=m1cq_7&944$tme&7(dcde!1i%zu"

DEBUG = True
ALLOWED_HOSTS = ["*"]  # dev only

# === APPLICATIONS ===
INSTALLED_APPS = [
    # Django apps de base
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Sites & Auth
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",

    # Outils externes / libs
    "django_extensions",

    # API / Swagger
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",

    # Filtres DRF
    "django_filters",

    # Apps projet
    "photos",
    "billing",
    "cv_generator",
    "authentification",
    "MotivationLetterApp",
    "eligibility",
    "core",
    "radar",

    # Module ajouté
    "preparation_tests",
]

# === MIDDLEWARE ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# === ROUTES ===
ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# === TEMPLATES ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

# === BASE DE DONNÉES ===
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# === INTERNATIONALISATION ===
LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("fr", _("French")),
    ("en", _("English")),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# === STATIC & MEDIA ===
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# === AUTH ===
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]

# Redirections spécifiques (conservées)
LOGIN_URL = "/authentification/login"
LOGIN_REDIRECT_URL = "/cv-generator/cv/list/"

# === REST FRAMEWORK ===
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_CLASSES": ["radar.throttling.RadarScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "200/day",
        "opportunities-list": "60/min",
        "subscriptions": "10/min",
    },
}

# === EMAIL ===
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.hostinger.com"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = "e-shelle_service@e-shelle.com"
EMAIL_HOST_PASSWORD = "Leoneldodo12."
DEFAULT_FROM_EMAIL = "e-shelle_service@e-shelle.com"

# === MODEL DEFAULT FIELD ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
