import os
import sys
from pathlib import Path
# ensure project root is on sys.path so settings package can be imported
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
print('CWD=', Path.cwd())
print('sys.path[0]=', sys.path[0])
os.environ.setdefault('DJANGO_SETTINGS_MODULE','videostory_local_ai.settings')
import django
django.setup()
from django.conf import settings
from django.apps import apps
print('DJANGO', django.get_version())
print('INSTALLED_APPS:', settings.INSTALLED_APPS)
print('APP CONFIGS:')
for app in apps.get_app_configs():
    print('-', app.name, app.path)