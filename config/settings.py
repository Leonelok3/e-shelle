"""
Fichier de configuration Django du projet immigration97.
Optimisé et stabilisé pour supporter tous les modules (dont visaetude, preparation_tests, etc.)
"""

from pathlib import Path
import os
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Chargement des variables d'environnement (.env)
load_dotenv()

# === CONFIG GÉNÉRALE ===
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-r-#hl^4p=7e5)hwqn#moz4=m1cq_7&944$tme&7(dcde!1i%zu"
DEBUG = True
ALLOWED_HOSTS = ["*"]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# === APPLICATIONS ===
INSTALLED_APPS = [
    # Django apps de base
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Sites / Authentification
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",

    # Outils utiles
    "django_extensions",
    "widget_tweaks",
    "django_filters",

    # API & DRF
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",

    # Applications internes
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
    'EnglishPrepApp.apps.EnglishprepappConfig',
    "GermanPrepApp.apps.GermanprepappConfig",
    'VisaTourismeApp',
    'DocumentsApp',

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

# === ROUTES PRINCIPALES ===
ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# === TEMPLATES ===
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
                "visaetude.context_processors.visa_progress",

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
    ("fr", _("Français")),
    ("en", _("Anglais")),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# === STATIC & MEDIA ===
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# === AUTHENTIFICATION ===
LOGIN_URL = "/authentification/login"
LOGIN_REDIRECT_URL = "/cv-generator/cv/list/"
LOGOUT_REDIRECT_URL = "/"

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]

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

# === DEFAULT FIELD ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === CRON (Optionnel) ===
"""
Pour éviter l’erreur 'django_cron introuvable', le cron est désactivé par défaut.
Tu pourras le réactiver plus tard quand tu installeras django-cron.
"""
# from django_cron import CronJobBase, Schedule
# from preparation_tests.management.commands.update_tef_content import Command as UpdateCommand

# class WeeklyTEFUpdater(CronJobBase):
#     RUN_EVERY_MINS = 10080  # toutes les 7 jours
#     schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
#     code = "preparation_tests.weekly_tef_updater"
# 
#     def do(self):
#         UpdateCommand().handle()


# Email de base pour l’envoi
DEFAULT_FROM_EMAIL = "no-reply@e-shelle.com"

# À adapter selon ton fournisseur (Gmail, etc.)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "TON_EMAIL"
EMAIL_HOST_PASSWORD = "TON_MOT_DE_PASSE_OU_APP_PASSWORD"
