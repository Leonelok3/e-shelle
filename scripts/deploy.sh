#!/bin/bash
# =============================================================
# deploy.sh — Script de déploiement complet Immigration97
# Usage : bash /var/www/e-shelle/scripts/deploy.sh
# =============================================================

set -e  # Arrête en cas d'erreur

PROJECT_DIR="/var/www/e-shelle"
VENV="$PROJECT_DIR/venv"
PYTHON="$VENV/bin/python"
MANAGE="$PYTHON $PROJECT_DIR/manage.py"
LOG_FILE="$PROJECT_DIR/logs/deploy.log"

# Créer le dossier logs si nécessaire
mkdir -p "$PROJECT_DIR/logs"

echo "============================================="
echo "[DEPLOY] $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================="

# 1. Récupérer le dernier code
echo ""
echo "[1/5] git pull..."
cd "$PROJECT_DIR"
git pull origin main

# 2. Installer les dépendances Python (si requirements.txt a changé)
echo ""
echo "[2/5] pip install..."
"$VENV/bin/pip" install -r requirements.txt --quiet

# 3. Appliquer les migrations (CRITIQUE — ne jamais oublier)
echo ""
echo "[3/5] python manage.py migrate..."
$MANAGE migrate --no-input

# 4. Collecter les fichiers statiques
echo ""
echo "[4/5] collectstatic..."
$MANAGE collectstatic --no-input --clear -v 0

# 5. Redémarrer gunicorn
echo ""
echo "[5/5] systemctl restart gunicorn..."
systemctl restart gunicorn.service

echo ""
echo "============================================="
echo "[DEPLOY] OK — $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================="

# Vérification rapide
echo ""
echo "[INFO] Migrations en attente :"
$MANAGE showmigrations --list | grep "\[ \]" || echo "  Aucune migration en attente."

echo ""
echo "[INFO] Vérification gunicorn :"
systemctl status gunicorn.service --no-pager -l | head -5
