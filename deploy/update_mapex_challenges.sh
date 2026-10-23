#!/usr/bin/env bash
# Targeted release for EduCam/Mapex challenges and the Facebook Agent.
# Run as root on the existing production VPS after pulling the release commit.
set -Eeuo pipefail
umask 027

APP=/home/eshelle/app
PY="$APP/.venv/bin/python"
BACKUP_ROOT=/home/eshelle/backups/mapex-facebook

[[ "$(id -u)" == 0 ]] || { echo "Run this script as root." >&2; exit 1; }
[[ -x "$PY" && -f "$APP/.env" ]]
cd "$APP"
exec 9>/run/lock/eshelle-mapex-facebook-deploy.lock
flock -n 9 || { echo "A Mapex/Facebook deployment is already running." >&2; exit 1; }

[[ "$(systemctl show eshelle -p WorkingDirectory --value)" == "$APP" ]]
systemctl is-active --quiet eshelle
[[ "$(sudo -u eshelle git -C "$APP" branch --show-current)" == "main" ]]
[[ -z "$(sudo -u eshelle git -C "$APP" status --porcelain --untracked-files=no)" ]] || {
  echo "Tracked production changes exist; refusing to overwrite server work." >&2
  exit 1
}
sudo -u eshelle git -C "$APP" fetch origin main --quiet
[[ "$(sudo -u eshelle git -C "$APP" rev-parse HEAD)" == "$(sudo -u eshelle git -C "$APP" rev-parse origin/main)" ]] || {
  echo "Production checkout is not at origin/main. Pull the release commit first." >&2
  exit 1
}

sudo -u eshelle "$PY" "$APP/manage.py" check
sudo -u eshelle "$PY" "$APP/manage.py" makemigrations --check --dry-run
sudo -u eshelle "$PY" "$APP/manage.py" shell -c 'from pathlib import Path; from django.conf import settings; ok = bool(settings.GOOGLE_API_KEY or settings.GEMINI_SEARCH_API_KEY or (settings.GCP_VERTEX_KEY_PATH and Path(settings.GCP_VERTEX_KEY_PATH).is_file())); print("MAPEX_GEMINI_CONFIGURED=" + str(ok)); raise SystemExit(0 if ok else 2)'

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$BACKUP_ROOT/$STAMP"
install -d -m 0700 -o eshelle -g eshelle "$BACKUP_ROOT"
install -d -m 0700 -o eshelle -g eshelle "$BACKUP"
sudo -u eshelle git -C "$APP" rev-parse HEAD > "$BACKUP/release-commit.txt"
sudo -u eshelle "$PY" "$APP/deploy/backup_studio_database.py" "$BACKUP"
trap 'echo "Release stopped. Database backup: '"$BACKUP"'. Inspect logs before retrying." >&2' ERR

sudo -u eshelle "$PY" "$APP/manage.py" migrate edu_platform --noinput
sudo -u eshelle "$PY" "$APP/manage.py" migrate facebook_agent --noinput
sudo -u eshelle "$PY" "$APP/manage.py" check
sudo -u eshelle "$PY" "$APP/manage.py" collectstatic --noinput

systemctl restart eshelle eshelle-celery eshelle-celerybeat
systemctl is-active --quiet eshelle
systemctl is-active --quiet eshelle-celery
systemctl is-active --quiet eshelle-celerybeat
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --max-time 30 --output /dev/null https://e-shelle.com/edu/
HTTP_CODE="$(curl --silent --show-error --retry 3 --retry-delay 2 --retry-connrefused --max-time 30 --output /dev/null --write-out '%{http_code}' https://e-shelle.com/edu/admin/challenges/)"
[[ "$HTTP_CODE" == "302" || "$HTTP_CODE" == "200" ]] || { echo "Unexpected challenge manager HTTP status: $HTTP_CODE" >&2; exit 1; }

echo "Mapex challenges and Facebook Agent deployed. Database backup: $BACKUP"
sudo -u eshelle git -C "$APP" log -1 --format='%h %s'
