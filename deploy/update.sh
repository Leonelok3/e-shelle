#!/bin/bash
##############################################################################
#  update.sh — Mise à jour du code en production (sans coupure)
#  Exécuter : sudo bash update.sh
##############################################################################
set -e

APP_USER="eshelle"
APP_DIR="/home/$APP_USER/app"

echo "→ Pull du code..."
sudo -u $APP_USER git -C "$APP_DIR" pull origin main

echo "→ Installation des nouvelles dépendances..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

echo "→ Migrations..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput

echo "→ Migrations Simplo..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput --settings=simplo.core.settings

echo "→ Collecte des statiques..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput

echo "→ Données de départ E-Shelle Jobs..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_jobs || true
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_transport || true
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_sante || true

echo "→ Collecte des statiques Simplo..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput --settings=simplo.core.settings

echo "→ Correction permissions staticfiles..."
chmod o+x /home/eshelle /home/eshelle/app
chmod -R o+r /home/eshelle/app/staticfiles/
chmod -R o+r /home/eshelle/app/simplo/staticfiles/ 2>/dev/null || true
chmod -R o+r /home/eshelle/app/simplo/media/ 2>/dev/null || true

echo "→ Rechargement Gunicorn (gracieux)..."
systemctl reload eshelle 2>/dev/null || systemctl restart eshelle
systemctl reload simplo 2>/dev/null || systemctl restart simplo

echo "✅ Mise à jour terminée — aucune coupure de service."
