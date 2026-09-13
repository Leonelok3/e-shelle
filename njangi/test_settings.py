"""Isolated Njangi tests: in-memory DB, no application data or external APIs."""
from adgen.test_settings import *

INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ("audio_studio", "adgen")] + ["njangi"]
ROOT_URLCONF = "njangi.test_urls"
LANGUAGE_CODE = "fr-fr"
