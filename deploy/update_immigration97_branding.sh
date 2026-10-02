#!/usr/bin/env bash
# Existing VPS, as root, after pulling the reviewed commit.
set -Eeuo pipefail
umask 027
APP=/home/eshelle/app
PY="$APP/.venv/bin/python"
[[ "$(id -u)" == 0 ]] || { echo "Lancer en tant que root." >&2; exit 1; }
cd "$APP"
exec 9>/run/lock/eshelle-immigration97-deploy.lock
flock -n 9 || { echo "Déploiement déjà en cours." >&2; exit 1; }
[[ -z "$(sudo -u eshelle git status --porcelain --untracked-files=no)" ]] || {
  echo "Fichiers suivis modifiés : arrêt pour les préserver." >&2; exit 1;
}
[[ "$(systemctl show eshelle -p WorkingDirectory --value)" == "$APP" ]]
systemctl is-active --quiet eshelle
sudo -u eshelle "$PY" manage.py check
BACKUP="/home/eshelle/backups/immigration97/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 -o eshelle -g eshelle "$BACKUP"
sudo -u eshelle git rev-parse HEAD > "$BACKUP/release-commit.txt"
sudo -u eshelle "$PY" deploy/backup_studio_database.py "$BACKUP"
trap 'echo "Déploiement interrompu. Sauvegarde : $BACKUP" >&2' ERR
# Branding changes only: no migration, subscription or price changes.
systemctl restart eshelle
systemctl is-active --quiet eshelle
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --output /dev/null https://immigration97.com/prep/fr/tcf/
sudo -u eshelle "$PY" deploy/check_immigration97_branding.py
sudo -u eshelle "$PY" manage.py shell -c 'from django.conf import settings; print("Expediteur email dedie configure :", bool(settings.IMMIGRATION97_DEFAULT_FROM_EMAIL)); print("Google dedie configure :", bool(settings.IMMIGRATION97_GOOGLE_CLIENT_ID and settings.IMMIGRATION97_GOOGLE_CLIENT_SECRET))'
echo "Immigration97 mis à jour. Sauvegarde : $BACKUP"
sudo -u eshelle git log -1 --format='%h %s'
