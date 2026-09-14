#!/usr/bin/env bash
# Run as root from the VPS. No content imports or paid generation during deployment.
set -euo pipefail
cd /home/eshelle/app
sudo -u eshelle .venv/bin/python manage.py check
sudo -u eshelle .venv/bin/python manage.py check_content_generation
sudo -u eshelle .venv/bin/python manage.py collectstatic --noinput
systemctl restart eshelle
systemctl is-active --quiet eshelle
for unit in eshelle-celery eshelle-celerybeat; do
    if [[ "$(systemctl show "$unit" -p LoadState --value)" == "loaded" ]]; then
        systemctl restart "$unit"
        systemctl is-active --quiet "$unit"
    fi
done
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --output /dev/null https://e-shelle.com/jobs/canada/
echo 'Code Canada/Allemagne chargé. Vérifiez les tâches de collecte et les parcours de génération.'
