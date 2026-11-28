#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE=${1:?Commit requis}
BASE=63397013d2e0d99c806c1ff480280c11dc465ca5
WEB=eshelle.service
WORKER=eshelle-celery.service
BEAT=eshelle-celerybeat.service
TIMER=eshelle-studio-renders.timer
RENDER=eshelle-studio-renders.service
[[ $EUID == 0 && $RELEASE =~ ^[0-9a-f]{40}$ ]]
exec 9>/run/lock/eshelle-business-deploy.lock
flock -n 9 || { echo 'Un déploiement E-Shelle est déjà en cours.' >&2; exit 1; }
exec 8>/run/lock/eshelle-studio-deploy.lock
flock -n 8 || { echo 'Un déploiement AdGen est déjà en cours.' >&2; exit 1; }

APP=$(systemctl show "$WEB" -p WorkingDirectory --value)
APP_USER=$(systemctl show "$WEB" -p User --value)
: "${APP:?Répertoire introuvable}" "${APP_USER:?Utilisateur du service introuvable}"
GIT_USER=$(stat -c %U "$APP/.git")
repo() { sudo -n -H -u "$GIT_USER" git -C "$APP" "$@"; }
app() { sudo -n -H -u "$APP_USER" "$@"; }

STATUS=$(repo status --porcelain --untracked-files=no)
if [[ -n $STATUS ]]; then
    printf 'Arrêt. Modifications suivies sur le serveur.\n%s\n' "$STATUS" >&2
    exit 1
fi
PREVIOUS=$(repo rev-parse HEAD)
if [[ $PREVIOUS != "$BASE" || $(repo rev-parse "$RELEASE^") != "$BASE" ]]; then
    printf 'Arrêt. Version serveur %s. Version de départ requise %s.\n' "$PREVIOUS" "$BASE" >&2
    exit 1
fi

for service in "$WEB" "$WORKER" "$BEAT"; do
    systemctl is-active --quiet "$service"
    [[ $(systemctl show "$service" -p WorkingDirectory --value) == "$APP" ]]
done
for unit in "$RENDER" "$TIMER"; do
    state=$(systemctl show "$unit" -p LoadState --value)
    case $state in
        loaded) ;;
        not-found)
            [[ $APP == /home/eshelle/app && $APP_USER == eshelle ]]
            ;;
        *) printf 'Unité systemd indisponible : %s (%s)\n' "$unit" "$state" >&2; exit 1 ;;
    esac
done
if [[ $(systemctl show "$RENDER" -p LoadState --value) == loaded ]]; then
    [[ $(systemctl show "$RENDER" -p WorkingDirectory --value) == "$APP" ]]
    [[ $(systemctl show "$RENDER" -p User --value) == "$APP_USER" ]]
fi
app sh -c 'command -v ffmpeg && command -v ffprobe' || { echo 'FFmpeg ou ffprobe manque sur le serveur.' >&2; exit 1; }
cd "$APP"
app .venv/bin/python manage.py check

check_renders_idle() {
    local render_state
    if [[ $(systemctl show "$RENDER" -p LoadState --value) == loaded ]]; then
        render_state=$(systemctl show "$RENDER" -p ActiveState --value)
        if [[ $render_state == active || $render_state == activating || $render_state == reloading ]]; then
            echo 'Un montage AdGen est en cours. Attends sa fin avant de relancer.' >&2
            return 1
        fi
    fi
    app .venv/bin/python manage.py shell -c '
from adgen.models import StudioUsage
if StudioUsage.objects.filter(resource="video", status="running").exists():
    raise SystemExit("Un montage AdGen reste en cours. Attends sa fin avant de relancer.")
'
}
check_renders_idle

timer_was_active=0
if systemctl is-active --quiet "$TIMER"; then timer_was_active=1; fi
BACKUP=$(mktemp -d /var/backups/eshelle-adgen.XXXXXX)
chown "$APP_USER" "$BACKUP"
migration_started=0
on_error() {
    local status=$?
    trap - ERR
    printf 'Déploiement interrompu. Dossier de sauvegarde : %s\n' "$BACKUP" >&2
    if [[ $migration_started == 0 ]]; then
        if [[ $(repo rev-parse HEAD) == "$PREVIOUS" ]] || repo switch --detach "$PREVIOUS"; then
            systemctl start "$WEB" "$WORKER" "$BEAT" || true
            if [[ $timer_was_active == 1 ]]; then systemctl start "$TIMER" || true; fi
        fi
    else
        echo 'Le code et la base de la nouvelle version sont conservés pour le diagnostic des migrations et des services.' >&2
        systemctl --no-pager --lines=0 status "$WEB" "$WORKER" "$BEAT" "$TIMER" >&2 || true
    fi
    exit "$status"
}
trap on_error ERR

if [[ $timer_was_active == 1 ]]; then systemctl stop "$TIMER"; fi
check_renders_idle
systemctl stop "$BEAT" "$WEB" "$WORKER"
check_renders_idle
app .venv/bin/python deploy/backup_studio_database.py "$BACKUP"
repo switch --detach "$RELEASE"
app .venv/bin/python manage.py check
app .venv/bin/python manage.py shell -c '
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
required = {
    ("adgen", "0010_adcampaign_offer"),
    ("adgen", "0011_adcinemaclip"),
    ("whatsapp_commerce", "0021_adgen_render_attribution"),
}
executor = MigrationExecutor(connections["default"])
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
planned = {(migration.app_label, migration.name) for migration, backwards in plan if not backwards}
if planned != required or any(backwards for migration, backwards in plan):
    raise SystemExit(f"Plan inattendu. Manquantes : {sorted(required - planned)}. Autres : {sorted(planned - required)}.")
'

migration_started=1
app .venv/bin/python manage.py migrate --noinput
app .venv/bin/python manage.py migrate --check
for unit in "$RENDER" "$TIMER"; do
    if [[ $(systemctl show "$unit" -p LoadState --value) == not-found ]]; then
        install -m 0644 "$APP/deploy/$unit" "/etc/systemd/system/$unit"
    fi
done
systemctl daemon-reload
systemctl start "$WEB" "$WORKER" "$BEAT"
systemctl enable --now "$TIMER"

curl_options=(-fsS --max-time 15 --retry 6 --retry-delay 3 --retry-connrefused)
page=$(curl "${curl_options[@]}" "https://e-shelle.com/pub/studio/abonnements/?release=$RELEASE") || false
grep -F 'AdGen Studio' <<< "$page" >/dev/null
for service in "$WEB" "$WORKER" "$BEAT" "$TIMER"; do
    systemctl is-active --quiet "$service"
done
trap - ERR
printf 'Version AdGen vérifiée : %s\nSauvegarde : %s\n' "$RELEASE" "$BACKUP"
