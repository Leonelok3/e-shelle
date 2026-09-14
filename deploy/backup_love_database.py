"""Backup before Love migration. Run as the app user; never prints credentials."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_cm.settings')
import django
django.setup()
from django.conf import settings

destination = Path('/home/eshelle/love-backups')
destination.mkdir(mode=0o700, parents=True, exist_ok=True)
os.umask(0o077)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
db = settings.DATABASES['default']
if db['ENGINE'].endswith('sqlite3'):
    target = destination / f'before-love-{stamp}.sqlite3'
    with sqlite3.connect(str(db['NAME'])) as source, sqlite3.connect(str(target)) as backup:
        source.backup(backup)
elif db['ENGINE'].endswith('postgresql'):
    target = destination / f'before-love-{stamp}.dump'
    env = os.environ.copy()
    for setting, variable in [('HOST','PGHOST'),('PORT','PGPORT'),('USER','PGUSER'),('PASSWORD','PGPASSWORD'),('NAME','PGDATABASE')]:
        env[variable] = str(db.get(setting, ''))
    subprocess.run(['pg_dump', '--format=custom', '--file', str(target)], env=env, check=True)
else:
    raise SystemExit('Moteur non pris en charge : effectuer une sauvegarde avant de migrer.')
print(f'Sauvegarde créée : {target}')
