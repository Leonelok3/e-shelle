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

echo "→ Migrations Tchaslucpay..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput --settings=tchaslucpay.core.settings

echo "→ Collecte des statiques..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput --upload-unhashed-files
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/scripts/check_staticfiles.py"

echo "→ Données de départ E-Shelle Jobs..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_jobs || true
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_transport || true
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_sante || true
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_business_plans || true
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" normalize_eshelle_urls || true

echo "→ Collecte des statiques Simplo..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput --settings=simplo.core.settings

echo "→ Collecte des statiques Tchaslucpay..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput --settings=tchaslucpay.core.settings

echo "→ Collecte des statiques Avatar..."
sudo -u $APP_USER bash -lc "cd '$APP_DIR/videostory_local_ai' && '$APP_DIR/.venv/bin/python' manage.py collectstatic --noinput" || true

echo "→ Correction permissions staticfiles..."
PARENT_DIR="$(dirname "$APP_DIR")"
chmod o+x "$PARENT_DIR" "$APP_DIR"
chmod o+x "$APP_DIR/staticfiles/"
chmod -R o+r "$APP_DIR/staticfiles/"
chmod -R o+r "$APP_DIR/simplo/staticfiles/" 2>/dev/null || true
chmod -R o+r "$APP_DIR/simplo/media/" 2>/dev/null || true
chmod -R o+r "$APP_DIR/staticfiles_tchaslucpay/" 2>/dev/null || true
chmod -R o+r "$APP_DIR/media_tchaslucpay/" 2>/dev/null || true
chmod -R o+r "$APP_DIR/videostory_local_ai/staticfiles/" 2>/dev/null || true
chmod -R o+r "$APP_DIR/videostory_local_ai/media/" 2>/dev/null || true

echo "→ Rechargement Gunicorn (gracieux)..."
systemctl reload eshelle 2>/dev/null || systemctl restart eshelle
systemctl reload simplo 2>/dev/null || systemctl restart simplo
systemctl reload tchaslucpay 2>/dev/null || systemctl restart tchaslucpay
systemctl reload avatar 2>/dev/null || systemctl restart avatar 2>/dev/null || true
systemctl restart eshelle-celery 2>/dev/null || true
systemctl restart eshelle-celerybeat 2>/dev/null || true

echo "✅ Mise à jour terminée — aucune coupure de service."
