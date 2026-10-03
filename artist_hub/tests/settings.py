from pathlib import Path
import tempfile
BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = "artist-hub-tests-only"
DEBUG = True
USE_TZ = True
TIME_ZONE = "Africa/Douala"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
                  "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "artist_hub"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "artist_hub.tests.urls"
MIDDLEWARE = ["django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
              "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware"]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "tests@example.com"
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
_test_files = tempfile.TemporaryDirectory(prefix="artist-hub-tests-")
MEDIA_ROOT = Path(_test_files.name) / "media"
ARTIST_HUB_PRIVATE_ROOT = Path(_test_files.name) / "private"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
ARTIST_HUB = {"ACTIVE_PAYMENT_PROVIDER": "mock"}
