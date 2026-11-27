#!/usr/bin/env bash
# Run the exact release copy of this script as root on the E-Shelle EC2 instance.
set -Eeuo pipefail

RELEASE=${1:?Commit de la version requis}
PREVIOUS_EXPECTED=d3ce0b84d8fd88653c3e7f891d3cdee86f91ef3c
SERVICES=(eshelle.service eshelle-celery.service eshelle-celerybeat.service)
[[ $EUID == 0 && $RELEASE =~ ^[0-9a-f]{40}$ ]]
exec 9>/run/lock/eshelle-business-deploy.lock
flock -n 9 || { echo 'Un déploiement est déjà en cours.' >&2; exit 1; }

APP=$(systemctl show eshelle.service -p WorkingDirectory --value)
APP_USER=$(systemctl show eshelle.service -p User --value)
[[ $APP == /* && -n $APP_USER && -x $APP/.venv/bin/python && -d $APP/.git ]]
GIT_USER=$(stat -c %U "$APP/.git")
repo() { sudo -n -H -u "$GIT_USER" git -C "$APP" "$@"; }
app() { sudo -n -H -u "$APP_USER" "$@"; }

for service in "${SERVICES[@]}"; do
    [[ $(systemctl show "$service" -p LoadState --value) == loaded ]]
    [[ $(systemctl show "$service" -p WorkingDirectory --value) == "$APP" ]]
    systemctl is-active --quiet "$service"
done

if [[ -n $(repo status --porcelain --untracked-files=no) ]]; then
    echo 'Arrêt. Le dépôt serveur contient des modifications suivies.' >&2
    exit 1
fi
PREVIOUS=$(repo rev-parse HEAD)
if [[ $PREVIOUS == "$RELEASE" ]]; then
    echo "La version $RELEASE est déjà sélectionnée. Vérifiez les migrations et les services." >&2
    exit 1
fi
if [[ $PREVIOUS != "$PREVIOUS_EXPECTED" || $(repo rev-parse "$RELEASE^") != "$PREVIOUS" ]]; then
    printf 'Versions inattendues. Serveur : %s. Base requise : %s\n' "$PREVIOUS" "$PREVIOUS_EXPECTED" >&2
    exit 1
fi

cd "$APP"
app .venv/bin/python manage.py check
BACKUP=$(mktemp -d /var/backups/eshelle-business.XXXXXX)
chown "$APP_USER" "$BACKUP"
migration_started=0
on_error() {
    local status=$?
    trap - ERR
    printf 'Déploiement interrompu. Sauvegarde : %s\n' "$BACKUP" >&2
    if [[ $migration_started == 0 ]]; then
        if [[ $(repo rev-parse HEAD) == "$PREVIOUS" ]] || repo switch --detach "$PREVIOUS"; then
            systemctl start "${SERVICES[@]}" || true
        fi
    else
        echo 'La migration a démarré. Le code de la nouvelle version et la base sont conservés pour le diagnostic.' >&2
        systemctl --no-pager --lines=0 status "${SERVICES[@]}" >&2 || true
    fi
    exit "$status"
}
trap on_error ERR

systemctl stop eshelle-celerybeat.service
systemctl stop eshelle.service
systemctl stop eshelle-celery.service
app .venv/bin/python deploy/backup_studio_database.py "$BACKUP"
repo switch --detach "$RELEASE"
app .venv/bin/python manage.py check
app .venv/bin/python manage.py shell -c '
from django.db import connections
from django.db.migrations.executor import MigrationExecutor

expected = {
    "billing": ["0009_partner_sale_attribution"],
    "business": ["0039_business_growth_follow_up", "0040_manual_provider_payment_channels"],
    "whatsapp_commerce": [
        "0013_catalog_forwarding", "0014_attach_forwarded_catalog_photo", "0015_offer_tracking",
        "0016_business_follow_ups", "0017_operational_workflows", "0018_agent_center_and_fulfillment",
        "0019_crm_quotes_and_availability_alerts", "0020_catalog_and_campaign_history",
    ],
}
executor = MigrationExecutor(connections["default"])
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
planned = {(migration.app_label, migration.name) for migration, backwards in plan if not backwards}
required = {(app, name) for app, names in expected.items() for name in names}
if planned != required or any(backwards for migration, backwards in plan):
    raise SystemExit(f"Plan de migrations inattendu. Manquantes : {sorted(required - planned)}. Autres : {sorted(planned - required)}.")
'

migration_started=1
app .venv/bin/python manage.py migrate --noinput
app .venv/bin/python manage.py migrate --check
systemctl start "${SERVICES[@]}"

curl_options=(--fail --silent --show-error --max-time 15 --retry 7 --retry-delay 3 --retry-connrefused)
curl "${curl_options[@]}" "https://e-shelle.com/immobilier/agences/?release=$RELEASE" -o /dev/null
sitemap=$(curl "${curl_options[@]}" "https://e-shelle.com/sitemap-produits.xml?release=$RELEASE")
grep -F '<sitemapindex' <<< "$sitemap" >/dev/null
robots=$(curl "${curl_options[@]}" "https://e-shelle.com/robots.txt?release=$RELEASE")
grep -F 'Sitemap: https://e-shelle.com/sitemap-produits.xml' <<< "$robots" >/dev/null

for service in "${SERVICES[@]}"; do
    systemctl is-active --quiet "$service"
done
printf 'Version vérifiée : %s\nSauvegarde : %s\n' "$RELEASE" "$BACKUP"
