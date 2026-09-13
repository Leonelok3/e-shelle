#!/usr/bin/env bash
# Existing VPS update only. Does not recreate .env, databases, media or Nginx.
set -Eeuo pipefail
umask 027
APP=/home/eshelle/app
PY="$APP/.venv/bin/python"
if [[ "$(id -u)" != 0 ]]; then
  echo "Lancer avec sudo bash deploy/update_adgen_studio.sh" >&2
  exit 1
fi
cd "$APP"
exec 9>/run/lock/eshelle-studio-deploy.lock
flock -n 9 || { echo "Un déploiement Studio est déjà en cours." >&2; exit 1; }
[[ -x "$PY" && -f "$APP/.env" ]]
if [[ -n "$(sudo -u eshelle git status --porcelain --untracked-files=no)" ]]; then
  echo "Modifications suivies présentes sur le VPS : arrêt pour les préserver." >&2
  exit 1
fi
systemctl is-active --quiet eshelle
if [[ "$(systemctl show eshelle -p WorkingDirectory --value)" != "$APP" ]]; then
  echo "Le service eshelle ne cible pas le dossier attendu. Vérifiez sa configuration." >&2
  exit 1
fi
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  apt-get update
  apt-get install -y ffmpeg
fi
sudo -u eshelle "$PY" manage.py check
BACKUP="/home/eshelle/backups/adgen-studio/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 -o eshelle -g eshelle "$BACKUP"
sudo -u eshelle git rev-parse HEAD > "$BACKUP/release-commit.txt"
sudo -u eshelle git reflog -2 --format='%H %gs' > "$BACKUP/recent-code-history.txt"
sudo -u eshelle "$PY" deploy/backup_studio_database.py "$BACKUP"

echo "Application des migrations AdGen Studio..."
# Additive schema first: existing Gunicorn workers tolerate the new nullable fields.
sudo -u eshelle "$PY" manage.py migrate adgen 0008 --noinput
sudo -u eshelle "$PY" manage.py migrate accounts 0014 --noinput
sudo -u eshelle "$PY" manage.py check

install -m 0644 deploy/eshelle-studio-renders.service /etc/systemd/system/eshelle-studio-renders.service
install -m 0644 deploy/eshelle-studio-renders.timer /etc/systemd/system/eshelle-studio-renders.timer
systemctl daemon-reload
systemctl restart eshelle
systemctl enable --now eshelle-studio-renders.timer
systemctl is-active --quiet eshelle
systemctl is-active --quiet eshelle-studio-renders.timer

# No static assets were added or changed by this release; templates load from code.
CHECK_FILE=$(mktemp)
trap 'rm -f "$CHECK_FILE"' EXIT
curl --fail --silent --show-error --retry 4 --retry-delay 3 \
  https://e-shelle.com/pub/studio/abonnements/ -o "$CHECK_FILE"
grep -q 'AdGen Studio Essentiel' "$CHECK_FILE"
grep -q 'AdGen Studio Business' "$CHECK_FILE"
echo "AdGen Studio déployé. Page abonnements vérifiée."
echo "Sauvegarde : $BACKUP"
sudo -u eshelle git log -1 --format='%h %s'
