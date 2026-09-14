"""Isolated Love tests with real migrations, no production database or keys."""
from adgen.test_settings import *

INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ('audio_studio', 'adgen')] + ['boutique', 'formations', 'payments', 'rencontres']
ROOT_URLCONF = 'rencontres.test_urls'
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Douala'
RENCONTRES_SETTINGS = {'LIKES_PAR_JOUR_FREE': 15, 'SUPER_LIKES_PAR_JOUR_FREE': 1, 'MESSAGES_PAR_JOUR_FREE': -1}
MEDIA_ROOT = BASE_DIR / 'output' / 'love' / 'test_media'
