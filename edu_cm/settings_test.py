import os

os.environ["DATABASE_URL"] = ""
os.environ["USE_SQLITE"] = "true"
os.environ["WHATSAPP_DRY_RUN"] = "false"

from .settings import *

DEBUG = True
DATABASE_URL = ""
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CAMPAY_MODE = "sandbox"
CAMPAY_TOKEN = ""
CAMPAY_USERNAME = ""
CAMPAY_PASSWORD = ""
OPENAI_API_KEY = ""
ELEVENLABS_API_KEY = ""
GOOGLE_API_KEY = ""
GEMINI_SEARCH_API_KEY = ""
FACEBOOK_AGENT_AUTO_PUBLISH_ENABLED = False
FACEBOOK_AUTO_SHARE_ENABLED = False
WHATSAPP_TOKEN = ""
WHATSAPP_DRY_RUN = True
WHATSAPP_VERIFY_TOKEN = ""
WHATSAPP_APP_SECRET = ""
WHATSAPP_CONFIG_READY = False
WHATSAPP_COMMERCE_ENABLED = False
WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED = False
WHATSAPP_COMMERCE_AI_ENABLED = False
CELERY_TASK_ALWAYS_EAGER = True
