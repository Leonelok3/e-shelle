from adgen.test_settings import *
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "business", "commercial_agent", "whatsapp_agent"]
AUTH_USER_MODEL = "auth.User"
ROOT_URLCONF = "commercial_agent.test_urls"
MIGRATION_MODULES = {"business": None, "whatsapp_agent": None}
MIGRATION_MODULES["commercial_agent"] = None
