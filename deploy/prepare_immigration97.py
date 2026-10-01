"""Run with the VPS virtualenv as root after staging the reviewed files."""
from pathlib import Path
from datetime import datetime, timezone
import shutil
import subprocess

app = Path('/home/eshelle/app')
stage = Path('/root/immigration97-stage')
backup = Path('/root/immigration97-backup-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
backup.mkdir(mode=0o700)
settings = app / 'edu_cm/settings.py'
env = app / '.env'
for source, name in [(settings, 'settings.py'), (env, '.env'),
                     (Path('/etc/nginx/sites-available/eshelle'), 'eshelle.nginx')]:
    shutil.copy2(source, backup / name)
(backup / 'nginx-active.txt').write_bytes(subprocess.check_output(['nginx', '-T'], stderr=subprocess.STDOUT))
print('BACKUP:', backup, flush=True)
text = settings.read_text()
entry = '    "edu_cm.immigration_domain.ImmigrationDomainMiddleware",\n'
anchor = '    "django.middleware.security.SecurityMiddleware",\n'
assert anchor in text
assert not Path('/etc/nginx/sites-enabled/immigration97').exists(), 'Site already enabled; review before proceeding'
if (app / 'edu_cm/immigration_domain.py').exists():
    assert (app / 'edu_cm/immigration_domain.py').read_bytes() == (stage / 'immigration_domain.py').read_bytes()
try:
    for name in ('immigration_domain.py', 'test_immigration_domain.py'):
        target = app / 'edu_cm' / name
        shutil.copyfile(stage / name, target)
        shutil.chown(target, user='eshelle', group='eshelle')
        target.chmod(0o644)
    if entry not in text:
        text = text.replace(anchor, anchor + entry, 1)
    marker = 'CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(DEFAULT_CSRF_ORIGINS))'
    domain_settings = '\nALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS + ["immigration97.com", "www.immigration97.com"]))\nCSRF_TRUSTED_ORIGINS += ["https://immigration97.com", "https://www.immigration97.com"]\n'
    assert marker in text
    settings.write_text(text.replace(marker, marker + domain_settings, 1))
    python = str(app / '.venv/bin/python')
    subprocess.run(['runuser', '-u', 'eshelle', '--', python, 'manage.py', 'check'], cwd=app, check=True)
    subprocess.run(['runuser', '-u', 'eshelle', '--', python, 'manage.py', 'test',
                    'edu_cm.test_immigration_domain', '--settings=preparation_tests.test_settings'], cwd=app, check=True)
except Exception:
    shutil.copy2(backup / 'settings.py', settings)
    raise
subprocess.run(['systemctl', 'reload', 'eshelle'], check=True)
# Serve only ACME until DNS and TLS are ready. Never expose login over HTTP.
http = '''server {
    listen 80;
    listen [::]:80;
    server_name immigration97.com www.immigration97.com;
    location /.well-known/acme-challenge/ { root /var/www/letsencrypt; }
    location / { return 503; }
}
'''
site = Path('/etc/nginx/sites-available/immigration97')
assert not site.exists(), 'Site already exists; review before proceeding'
site.write_text(http)
Path('/etc/nginx/sites-enabled/immigration97').symlink_to(site)
subprocess.run(['nginx', '-t'], check=True)
subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
print('Prepared application and HTTP challenge. TLS and DNS still pending.', flush=True)
