#!/bin/bash
set -e

echo "🚀 Déploiement Immigration97..."

cd /var/www/e-shelle

echo "📥 Pull depuis GitHub"
git pull origin main

echo "🐍 Activation venv"
source venv/bin/activate

echo "📦 Installation dépendances"
pip install -r requirements.txt

echo "🗄️ Migrations Django"
python manage.py migrate --noinput

echo "🎨 Collect static"
python manage.py collectstatic --noinput

echo "🔄 Redémarrage Gunicorn"
systemctl restart immigration97

echo "✅ Déploiement terminé"

