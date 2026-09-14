#!/usr/bin/env bash
# Run from your VPS session: sudo bash /home/eshelle/app/deploy/update_love.sh
set -euo pipefail
cd /home/eshelle/app
sudo -u eshelle .venv/bin/python manage.py check
sudo -u eshelle .venv/bin/python deploy/backup_love_database.py
sudo -u eshelle .venv/bin/python manage.py migrate rencontres --noinput
sudo -u eshelle .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart eshelle
sudo systemctl is-active --quiet eshelle
curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused --output /dev/null https://e-shelle.com/rencontres/premium/
sudo -u eshelle .venv/bin/python manage.py check_love_production
echo 'Love mis à jour. Vérifiez ensuite les parcours avec deux comptes de test.'
