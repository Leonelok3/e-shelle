#!/bin/bash
set -e
cd /var/www/e-shelle || exit 1

# Run git operations as repository owner
echo '--- GIT ---'
sudo -u e_shelleltd git fetch origin main || true
sudo -u e_shelleltd git status --porcelain || true
sudo -u e_shelleltd git rev-parse --abbrev-ref HEAD || true
sudo -u e_shelleltd git log -n 3 --oneline || true

echo '--- PULL ---'
sudo -u e_shelleltd git checkout main || true
sudo -u e_shelleltd git pull origin main || true

# Run Django commands using the venv if present
echo '--- VENV / MIGRATIONS ---'
if [ -f .venv/bin/activate ]; then
  sudo -u e_shelleltd bash -lc "source .venv/bin/activate && python manage.py showmigrations --plan" || true
else
  python manage.py showmigrations --plan || true
fi

echo '--- COLLECTSTATIC ---'
sudo -u e_shelleltd bash -lc "source .venv/bin/activate && python manage.py collectstatic --noinput" || true

# Restart / reload services
echo '--- RELOAD GUNICORN ---'
sudo systemctl reload gunicorn || sudo systemctl restart gunicorn || true

# Service status
echo '--- SERVICE STATUS ---'
sudo systemctl status gunicorn --no-pager -l || true
sudo systemctl status nginx --no-pager -l || true

# Journals
echo '--- JOURNALS (last 200 lines) ---'
sudo journalctl -u gunicorn -n 200 --no-pager || true
sudo journalctl -u nginx -n 200 --no-pager || true

# Smoke HTTP checks (localhost and public placeholder)
echo '--- SMOKE HTTP localhost ---'
curl -sI 'http://127.0.0.1/' || true
curl -sI 'http://127.0.0.1/business/' || true
curl -sI 'http://127.0.0.1/tarifs/' || true

echo '--- SMOKE HTTP public (if configured) ---'
curl -sI 'https://YOUR_DOMAIN/' || true
curl -sI 'https://YOUR_DOMAIN/business/' || true
curl -sI 'https://YOUR_DOMAIN/tarifs/' || true

# Fetch home HTML (may be large)
echo '--- FETCH HOME HTML ---'
curl -sS 'http://127.0.0.1/' || true

echo 'DONE'
