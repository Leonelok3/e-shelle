#!/usr/bin/env bash
# Execute on the VPS after pulling main.
set -euo pipefail
cd /home/eshelle/app
install -d -m 0700 -o eshelle -g eshelle /home/eshelle/whatsapp-backups
backup_path="/home/eshelle/whatsapp-backups/database-$(date -u +%Y%m%dT%H%M%SZ)"
sudo -u eshelle .venv/bin/python manage.py check
sudo -u eshelle .venv/bin/python deploy/backup_studio_database.py "$backup_path"
install -d -m 0700 -o eshelle -g eshelle data/whatsapp-private
sudo -u eshelle .venv/bin/python manage.py migrate whatsapp_agent --noinput
sudo -u eshelle .venv/bin/python manage.py collectstatic --noinput
install -D -m 0644 -o eshelle -g eshelle \
    whatsapp_agent/static/whatsapp_agent/js/inbox-media.js \
    staticfiles/whatsapp_agent/js/inbox-media.js
chmod o+rx staticfiles/whatsapp_agent staticfiles/whatsapp_agent/js
install -D -m 0644 -o eshelle -g eshelle \
    whatsapp_agent/static/whatsapp_agent/meta_selector.js \
    staticfiles/whatsapp_agent/meta_selector.js
sudo systemctl restart eshelle
if systemctl cat eshelle-celery.service >/dev/null 2>&1; then
    sudo systemctl restart eshelle-celery
    sudo systemctl is-active --quiet eshelle-celery
else
    echo 'Attention: service eshelle-celery absent. Les campagnes reelles necessitent un worker Celery.'
fi
sudo systemctl is-active --quiet eshelle
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused \
    'https://e-shelle.com/static/whatsapp_agent/js/inbox-media.js?v=20261003-1' \
    | cmp - staticfiles/whatsapp_agent/js/inbox-media.js
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused \
    'https://e-shelle.com/static/whatsapp_agent/meta_selector.js?v=20261003-1' \
    | cmp - staticfiles/whatsapp_agent/meta_selector.js
sudo -u eshelle .venv/bin/python manage.py check_whatsapp_delivery
echo 'WhatsApp mis a jour. Configurez le compte Meta puis selectionnez et enregistrez un modele dans la campagne avant le test.'
