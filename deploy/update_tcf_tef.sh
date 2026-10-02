#!/usr/bin/env bash
# Existing VPS only; execute as root after git pull --ff-only.
set -Eeuo pipefail
umask 027
APP=/home/eshelle/app
PY="$APP/.venv/bin/python"
[[ "$(id -u)" == 0 ]] || { echo "Lancer en tant que root." >&2; exit 1; }
cd "$APP"
exec 9>/run/lock/eshelle-tcf-tef-deploy.lock
flock -n 9 || { echo "Un déploiement TCF/TEF est déjà en cours." >&2; exit 1; }
[[ -x "$PY" && -f .env ]]
[[ -z "$(sudo -u eshelle git status --porcelain --untracked-files=no)" ]] || {
  echo "Des fichiers suivis sont modifiés sur le serveur. Arrêt pour les préserver." >&2; exit 1;
}
[[ "$(systemctl show eshelle -p WorkingDirectory --value)" == "$APP" ]]
systemctl is-active --quiet eshelle
sudo -u eshelle "$PY" manage.py check
BACKUP="/home/eshelle/backups/tcf-tef/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 -o eshelle -g eshelle "$BACKUP"
install -d -m 0700 -o eshelle -g eshelle "$APP/output/tcf_tef_quality"
sudo -u eshelle git rev-parse HEAD > "$BACKUP/release-commit.txt"
sudo -u eshelle git reflog -2 --format='%H %gs' > "$BACKUP/recent-code-history.txt"
sudo -u eshelle "$PY" deploy/backup_studio_database.py "$BACKUP"
trap 'echo "Déploiement interrompu. Sauvegarde : $BACKUP. Consulter la sortie avant de relancer." >&2' ERR
# No new migration; ensure the existing document_text migration is present.
sudo -u eshelle "$PY" manage.py migrate preparation_tests --noinput
for exam in tcf tef; do
  sudo -u eshelle "$PY" manage.py audit_learning_materials --exam "$exam" --all-levels > "$BACKUP/${exam}-before.json"
  sudo -u eshelle "$PY" manage.py repair_french_encoding --exam "$exam" --apply
  # Only explicit scripts; existing references survive a provider failure.
  sudo -u eshelle "$PY" manage.py generate_exercise_audio --exam "$exam" --all
  sudo -u eshelle "$PY" manage.py audit_learning_materials --exam "$exam" --all-levels --check-audio-files > "$BACKUP/${exam}-after.json"
done
sudo -u eshelle "$PY" manage.py prepare_tcf_daily_audio
sudo -u eshelle "$PY" manage.py collectstatic --noinput
sudo -u eshelle "$PY" manage.py check
systemctl restart eshelle
systemctl is-active --quiet eshelle
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --output /dev/null https://e-shelle.com/prep/fr/tcf/
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --output /dev/null https://e-shelle.com/prep/fr/tcf/du-jour/
echo "TCF/TEF mis à jour. Sauvegarde et audits : $BACKUP"
sudo -u eshelle git log -1 --format='%h %s'
