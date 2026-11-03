#!/usr/bin/env bash
# Narrow, backed-up release path for the daily TCF improvements.
set -Eeuo pipefail
umask 027
APP=/home/eshelle/app
PY="$APP/.venv/bin/python"
if [[ "$(id -u)" != 0 ]]; then
  echo "Lancer avec sudo bash deploy/update_tcf_daily.sh" >&2
  exit 1
fi
cd "$APP"
exec 9>/run/lock/eshelle-tcf-daily-deploy.lock
flock -n 9 || { echo "Un deploiement TCF quotidien est deja en cours." >&2; exit 1; }
[[ -x "$PY" && -f "$APP/.env" ]]
[[ -z "$(sudo -u eshelle git status --porcelain --untracked-files=no)" ]] || {
  echo "Des fichiers suivis sont modifies sur le serveur. Arret pour les preserver." >&2; exit 1;
}
[[ "$(systemctl show eshelle -p WorkingDirectory --value)" == "$APP" ]]
systemctl is-active --quiet eshelle

sudo -u eshelle "$PY" manage.py check
BACKUP="/home/eshelle/backups/tcf-daily/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 -o eshelle -g eshelle "$BACKUP"
sudo -u eshelle git rev-parse HEAD > "$BACKUP/release-commit.txt"
sudo -u eshelle git reflog -2 --format='%H %gs' > "$BACKUP/recent-code-history.txt"
sudo -u eshelle "$PY" deploy/backup_studio_database.py "$BACKUP"
trap 'echo "Deploiement interrompu. Sauvegarde disponible : $BACKUP" >&2' ERR

# The additive table stores the learner's daily progress; no old rows are rewritten.
sudo -u eshelle "$PY" manage.py migrate preparation_tests 0032_tcfdailyprogress --noinput
sudo -u eshelle "$PY" manage.py prepare_tcf_daily_audio
sudo -u eshelle "$PY" manage.py check_tcf_daily
sudo -u eshelle "$PY" manage.py collectstatic --noinput
install -D -m 0644 -o eshelle -g eshelle "$APP/static/css/tcf-daily.css" "$APP/staticfiles/css/tcf-daily.css"
install -D -m 0644 -o eshelle -g eshelle "$APP/static/js/tcf-daily.js" "$APP/staticfiles/js/tcf-daily.js"
install -m 0644 "$APP/deploy/eshelle-tcf-daily-health.service" /etc/systemd/system/eshelle-tcf-daily-health.service
install -m 0644 "$APP/deploy/eshelle-tcf-daily-health.timer" /etc/systemd/system/eshelle-tcf-daily-health.timer
systemctl daemon-reload
sudo -u eshelle "$PY" manage.py check

systemctl restart eshelle
systemctl enable --now eshelle-tcf-daily-health.timer
systemctl is-active --quiet eshelle
systemctl is-active --quiet eshelle-tcf-daily-health.timer
sudo -u eshelle "$PY" manage.py check_tcf_daily
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --output /dev/null https://e-shelle.com/prep/fr/tcf/
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --output /dev/null https://e-shelle.com/prep/fr/tcf/du-jour/
STATIC_CHECK=$(mktemp -d)
trap 'rm -rf -- "$STATIC_CHECK"' EXIT
for asset in css/tcf-daily.css js/tcf-daily.js; do
  curl --fail --silent --show-error --retry 3 --retry-delay 2 \
    "https://e-shelle.com/static/$asset?v=20261023-1" -o "$STATIC_CHECK/$(basename "$asset")"
  cmp "$APP/static/$asset" "$STATIC_CHECK/$(basename "$asset")"
done
echo "TCF quotidien deploye. Sauvegarde : $BACKUP"
sudo -u eshelle git log -1 --format='%h %s'
