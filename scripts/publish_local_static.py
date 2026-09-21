"""Publish local static files using Django, bypassing Cloudinary's override."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_cm.settings')

import django
django.setup()

from django.conf import settings
from django.core.management import call_command
from django.contrib.staticfiles.management.commands.collectstatic import Command
from django.contrib.staticfiles.storage import staticfiles_storage

destination = Path(staticfiles_storage.path('')).resolve()
expected = (ROOT / 'staticfiles').resolve()
if destination != expected or Path(settings.STATIC_ROOT).resolve() != expected:
    raise SystemExit('STOP: this command requires the project local staticfiles directory.')

# Pass the command object explicitly: do not resolve the Cloudinary override.
# No --clear: unrelated existing assets are preserved.
call_command(Command(), interactive=False, verbosity=1)

assets = [
    'img/immigration97-logo.png',
    'css/immigration97.css',
    'css/canada-navigation.css',
    'js/immigration97-drafts.js',
    'js/preparation_tests.js',
    'js/learning-feedback.js',
]
for name in assets:
    source = ROOT / 'static' / name
    published = expected / name
    if not published.is_file() or source.read_bytes() != published.read_bytes():
        raise SystemExit('Publication verification failed: ' + name)
    print(name + ' OK')
