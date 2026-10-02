"""Branding regression tests isolated from production data and providers."""
from preparation_tests.test_settings import *
INSTALLED_APPS = INSTALLED_APPS + ["django.contrib.sites", "allauth", "allauth.account", "allauth.socialaccount"]
MIDDLEWARE = MIDDLEWARE + ["allauth.account.middleware.AccountMiddleware"]
SITE_ID = 1
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "E-Shelle <test@example.com>"
ALLOWED_HOSTS = ALLOWED_HOSTS + ["e-shelle.com", "immigration97.com", "www.immigration97.com"]
