"""Content regression suite: SQLite test DB, no provider calls or production storage."""
from adgen.test_settings import *

INSTALLED_APPS = INSTALLED_APPS + [
    'ai_engine', 'jobs', 'germany_opportunities', 'canada_resume', 'lebenslauf',
    'GermanPrepApp', 'preparation_tests',
]
ROOT_URLCONF = 'ai_engine.test_content_urls'
AI_CONTENT_MODE = 'offline'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
