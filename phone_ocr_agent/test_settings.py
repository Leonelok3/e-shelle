from adgen.test_settings import *

INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "phone_ocr_agent"]
AUTH_USER_MODEL = "auth.User"
ROOT_URLCONF = "phone_ocr_agent.test_urls"
