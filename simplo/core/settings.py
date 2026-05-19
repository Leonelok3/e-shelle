from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

SECRET_KEY = os.getenv("SIMPLO_SECRET_KEY", "dev-simplo-change-me")
DEBUG = os.getenv("SIMPLO_DEBUG", "True").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("SIMPLO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "SIMPLO_CSRF_TRUSTED_ORIGINS",
        "https://simplo.e-shelle.com",
    ).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simplo.accounts.apps.AccountsConfig",
    "simplo.transport.apps.TransportConfig",
    "simplo.livraison.apps.LivraisonConfig",
    "simplo.courses.apps.CoursesConfig",
    "simplo.marketplace.apps.MarketplaceConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "simplo.core.urls"
WSGI_APPLICATION = "simplo.core.wsgi.application"
ASGI_APPLICATION = "simplo.core.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASE_URL = os.getenv("SIMPLO_DATABASE_URL", "")
if DATABASE_URL:
    import urllib.parse as _up

    _url = _up.urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _url.path.lstrip("/"),
            "USER": _url.username,
            "PASSWORD": _url.password,
            "HOST": _url.hostname,
            "PORT": str(_url.port or 5432),
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

AUTH_USER_MODEL = "simplo_accounts.CustomUser"

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "simplo_accounts:login"
LOGIN_REDIRECT_URL = "simplo_marketplace:home"
LOGOUT_REDIRECT_URL = "simplo_marketplace:home"

if not DEBUG:
    SESSION_COOKIE_SECURE = os.getenv("SIMPLO_SESSION_COOKIE_SECURE", "True").lower() in {"1", "true", "yes"}
    CSRF_COOKIE_SECURE = os.getenv("SIMPLO_CSRF_COOKIE_SECURE", "True").lower() in {"1", "true", "yes"}
    SECURE_HSTS_SECONDS = int(os.getenv("SIMPLO_SECURE_HSTS_SECONDS", "63072000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
