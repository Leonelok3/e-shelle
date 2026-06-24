#!/bin/bash
##############################################################################
#  deploy.sh — Script de déploiement E-Shelle sur VPS Ubuntu 22.04 / 24.04
#  Exécuter en tant que : sudo bash deploy.sh
#  Prérequis : domaine e-shelle.com pointant vers l'IP du serveur
##############################################################################
set -e

APP_USER="eshelle"
APP_DIR="/home/$APP_USER/app"
REPO="https://github.com/Leonelok3/e-shelle.git"
DOMAIN="e-shelle.com"
PYTHON="python3"

echo "======================================================================"
echo "  E-Shelle — Déploiement automatique"
echo "======================================================================"

# ── 1. Paquets système ──────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y -qq \
    $PYTHON python3-venv python3-dev python3-pip \
    postgresql postgresql-contrib \
    nginx certbot python3-certbot-nginx \
    git curl build-essential libpq-dev \
    redis-server tesseract-ocr tesseract-ocr-fra \
    supervisor
# ── 2. Utilisateur applicatif ───────────────────────────────────────────────
if ! id "$APP_USER" &>/dev/null; then
    adduser --system --group --home /home/$APP_USER --shell /bin/bash $APP_USER
    echo "✔  Utilisateur $APP_USER créé"
fi

# ── 3. Base de données PostgreSQL ───────────────────────────────────────────
echo "→ Configuration PostgreSQL..."
DB_PASSWORD=$(openssl rand -base64 24)
sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename='eshelle_user'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER eshelle_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='eshelle_db'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE eshelle_db OWNER eshelle_user;"
echo "✔  PostgreSQL configuré — mot de passe DB : $DB_PASSWORD"
echo "    ⚠️  Notez ce mot de passe, il sera mis dans .env"

# ── 4. Cloner / mettre à jour le dépôt ──────────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
    echo "→ Mise à jour du code..."
    sudo -u $APP_USER git -C "$APP_DIR" pull origin main
else
    echo "→ Clonage du dépôt..."
    sudo -u $APP_USER git clone "$REPO" "$APP_DIR"
fi

# ── 5. Environnement Python + dépendances ───────────────────────────────────
echo "→ Installation des dépendances Python..."
sudo -u $APP_USER $PYTHON -m venv "$APP_DIR/.venv"
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install --upgrade pip -q
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install \
    -r "$APP_DIR/requirements.txt" \
    psycopg2-binary \
    -q
echo "✔  Dépendances installées"

# ── 6. Fichier .env production ──────────────────────────────────────────────
if [ ! -f "$APP_DIR/.env" ]; then
    SECRET_KEY=$(openssl rand -base64 50 | tr -d '\n/+=' | head -c 50)
    cat > "$APP_DIR/.env" <<EOF
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN

DATABASE_URL=postgres://eshelle_user:$DB_PASSWORD@localhost:5432/eshelle_db

ANTHROPIC_API_KEY=sk-ant-REMPLACER_PAR_VOTRE_CLE
OPENAI_API_KEY=sk-REMPLACER_PAR_VOTRE_CLE_OPENAI

WHATSAPP_DRY_RUN=True
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=
WHATSAPP_VERIFY_TOKEN=un_secret_webhook_a_definir

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=django-db
DJANGO_LOG_FILE=/var/log/eshelle/django_errors.log

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=E-Shelle <contact@$DOMAIN>

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=63072000
EOF
    chown $APP_USER:$APP_USER "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo "✔  .env créé (éditez-le pour ajouter ANTHROPIC_API_KEY et SMTP)"
else
    echo "→ .env existant conservé"
fi

# ── 7. Django : migrations + static ─────────────────────────────────────────
echo "→ Migrations Django..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput

echo "→ Collecte des fichiers statiques..."
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput

# Superuser
echo "→ Superuser Django : à créer manuellement après déploiement si nécessaire."
echo "   Commande : sudo -u $APP_USER $APP_DIR/.venv/bin/python $APP_DIR/manage.py createsuperuser"

# ── 8. Permissions Nginx → staticfiles ──────────────────────────────────────
# Ubuntu crée les home dirs en 700 → www-data (Nginx) ne peut pas lire
chmod o+x /home/$APP_USER
chmod o+x "$APP_DIR"
chmod -R o+r "$APP_DIR/staticfiles/"
echo "✔  Permissions staticfiles corrigées pour Nginx"

# ── Logs ──────────────────────────────────────────────────────────────────────
mkdir -p /var/log/eshelle
chown $APP_USER:www-data /var/log/eshelle

# ── 9. Service systemd Gunicorn ─────────────────────────────────────────────
echo "→ Installation du service systemd..."
cp "$APP_DIR/deploy/eshelle.service" /etc/systemd/system/eshelle.service
systemctl daemon-reload
systemctl enable eshelle
systemctl restart eshelle
echo "✔  Service Gunicorn démarré"

# ── 10. Nginx ───────────────────────────────────────────────────────────────
echo "→ Configuration Nginx..."
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/eshelle

# Désactiver le site par défaut
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/eshelle /etc/nginx/sites-enabled/eshelle

nginx -t && systemctl reload nginx
echo "✔  Nginx configuré"

# ── 11. SSL avec Certbot ─────────────────────────────────────────────────────
echo "→ Génération du certificat SSL..."
certbot --nginx \
    --non-interactive \
    --agree-tos \
    --email "contact@$DOMAIN" \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --redirect || echo "⚠️  Certbot : vérifiez que DNS pointe vers ce serveur"

# Renouvellement auto
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && systemctl reload nginx") | crontab -

echo ""
echo "======================================================================"
echo "  ✅  Déploiement terminé !"
echo "======================================================================"
echo ""
echo "  URL       : https://$DOMAIN"
echo "  Admin     : https://$DOMAIN/admin/"
echo "  Admin     : créez-le avec python manage.py createsuperuser"
echo ""
echo "  ⚠️  Actions restantes :"
echo "     1. Éditez /home/$APP_USER/app/.env"
echo "        → Ajoutez ANTHROPIC_API_KEY"
echo "        → Ajoutez OPENAI_API_KEY si vous utilisez les agents GPT/images"
echo "        → Laissez WHATSAPP_DRY_RUN=True tant que Meta WhatsApp n'est pas prêt"
echo "        → Configurez SMTP (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD)"
echo "     2. Changez le mot de passe admin sur /admin/"
echo "     3. sudo systemctl restart eshelle"
echo ""
