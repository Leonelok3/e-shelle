from commercial_agent.test_settings import *

ROOT_URLCONF = "whatsapp_agent.test_urls"
WHATSAPP_DRY_RUN = False
WHATSAPP_TOKEN = "test-token"
WHATSAPP_PHONE_ID = "123"
WHATSAPP_API_URL = "https://graph.facebook.com/v23.0/123/messages"
WHATSAPP_DEFAULT_TEMPLATE = ""
WHATSAPP_CONFIG_READY = True
WHATSAPP_APP_SECRET = "test-secret"
MIDDLEWARE = MIDDLEWARE + ["django.middleware.csrf.CsrfViewMiddleware"]

