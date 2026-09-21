"""Isolated Studio tests: local SQLite, no real keys, storage or application DB."""
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "studio-tests-only"
DEBUG = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.CustomUser"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
                  "django.contrib.messages", "django.contrib.staticfiles", "curriculum", "accounts", "audio_studio", "adgen"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "adgen.test_urls"
MIDDLEWARE = ["django.contrib.sessions.middleware.SessionMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware"]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "output" / "adgen" / "test_media"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
LOGIN_URL = "/accounts/login/"
OPENAI_API_KEY = ""
GOOGLE_API_KEY = ""
ADGEN_VIDEO_FAST_MODE = True
ADGEN_VIDEO_FAST_WIDTH = 360
ADGEN_VIDEO_FAST_HEIGHT = 640
