#!/bin/bash
##############################################################################
#  update.sh — Mise à jour du code en production (sans coupure)
#  Exécuter : sudo bash update.sh
##############################################################################
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER=$(stat -c '%U' "$APP_DIR")

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
PARENT_DIR="$(dirname "$APP_DIR")"
chmod o+x "$PARENT_DIR" "$APP_DIR"
chmod -R o+r "$APP_DIR/staticfiles/"
chmod -R o+r "$APP_DIR/simplo/staticfiles/" 2>/dev/null || true
chmod -R o+r "$APP_DIR/simplo/media/" 2>/dev/null || true

echo "→ Rechargement Gunicorn (gracieux)..."
systemctl reload e-shelle 2>/dev/null || systemctl restart e-shelle
systemctl reload simplo 2>/dev/null || systemctl restart simplo
systemctl reload tchaslucpay 2>/dev/null || systemctl restart tchaslucpay

echo "✅ Mise à jour terminée — aucune coupure de service."
