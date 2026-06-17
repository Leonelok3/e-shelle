# Audit deploiement Hostinger - E-Shelle

Date: 2026-06-02

Objectif: verifier les points critiques avant de remettre E-Shelle sur le VPS Hostinger.

## Verdict rapide

Le projet est deployable sur VPS, mais il faut respecter l'ordre ci-dessous et ne pas oublier les variables sensibles. Les checks Django passent en local, les migrations sont coherentes, et les scripts de deploiement ont ete renforces.

## 1. Environnement `.env`

Fichier modele: `deploy/env.production`

Variables obligatoires a renseigner sur le VPS dans `/home/eshelle/app/.env`:

- `DJANGO_SECRET_KEY`: vraie cle longue et secrete.
- `DJANGO_DEBUG=False`.
- `DJANGO_ALLOWED_HOSTS`: `e-shelle.com`, `www.e-shelle.com` et les sous-domaines.
- `DATABASE_URL`: PostgreSQL local du VPS.
- `ANTHROPIC_API_KEY`: pour Claude si utilise.
- `OPENAI_API_KEY`: pour les agents GPT/images si utilise.
- `EMAIL_HOST_USER` et `EMAIL_HOST_PASSWORD`: SMTP reel.

Variables WhatsApp:

- `WHATSAPP_DRY_RUN=True` au depart.
- `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN` uniquement quand Meta est pret.
- Passer `WHATSAPP_DRY_RUN=False` seulement apres un test Meta valide.

Variables services:

- `CELERY_BROKER_URL=redis://localhost:6379/0`.
- `CELERY_RESULT_BACKEND=django-db`.
- `DJANGO_LOG_FILE=/var/log/eshelle/django_errors.log`.

## 2. Requirements

Le fichier `requirements.txt` contient les dependances Django, Gunicorn, WhiteNoise, PostgreSQL, Celery et IA.

Ajout important effectue:

- `pytesseract==0.3.13` pour le Phone OCR Agent.

Paquets systeme requis sur Ubuntu:

- `python3.12`, `python3.12-venv`, `python3.12-dev`.
- `postgresql`, `postgresql-contrib`.
- `nginx`, `certbot`, `python3-certbot-nginx`.
- `redis-server`.
- `tesseract-ocr`, `tesseract-ocr-fra`.
- `git`, `curl`, `build-essential`, `libpq-dev`.

## 3. Static et media

Commande a lancer sur le VPS:

```bash
sudo -u eshelle /home/eshelle/app/.venv/bin/python /home/eshelle/app/manage.py collectstatic --noinput
```

Nginx sert:

- `/static/` depuis `/home/eshelle/app/staticfiles/`.
- `/media/` depuis `/home/eshelle/app/media/`.

Important:

- Copier les images locales importantes vers `/home/eshelle/app/media/`.
- Verifier les permissions `www-data`.
- Ne pas supprimer `media/` pendant les redeploiements.

## 4. Gunicorn / systemd

Service principal: `deploy/eshelle.service`

Commande de controle:

```bash
sudo systemctl status eshelle
sudo systemctl restart eshelle
sudo journalctl -u eshelle -n 100 --no-pager
```

Le service lance `edu_cm.wsgi:application`.

Point a ajouter ensuite si les campagnes doivent tourner en arriere-plan:

- `celery.service`.
- `celerybeat.service`.

Pour l'instant, Redis est installe par les scripts, mais il faut ajouter ces services si on veut automatiser totalement les taches asynchrones.

## 5. Nginx

Configuration: `deploy/nginx.conf`

Points couverts:

- Domaine principal `e-shelle.com`.
- Sous-domaines E-Shelle.
- `staticfiles`.
- `media`.
- Proxy vers Gunicorn.
- Endpoint streaming IA.
- Certbot SSL.

Avant lancement:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 6. Migrations

Les checks locaux indiquent:

- `python manage.py check`: OK.
- `python manage.py makemigrations --check --dry-run`: OK.

Sur VPS:

```bash
sudo -u eshelle /home/eshelle/app/.venv/bin/python /home/eshelle/app/manage.py migrate --noinput
```

Important:

- Committer toutes les migrations non suivies avant deploy.
- Ne pas deployer si `makemigrations --check --dry-run` detecte de nouvelles migrations non creees.

## 7. Securite

Corrections effectuees:

- Suppression de la creation automatique d'un superuser avec mot de passe public.
- Le superuser doit etre cree manuellement:

```bash
sudo -u eshelle /home/eshelle/app/.venv/bin/python /home/eshelle/app/manage.py createsuperuser
```

Production:

- `SECURE_SSL_REDIRECT=True`.
- `SESSION_COOKIE_SECURE=True`.
- `CSRF_COOKIE_SECURE=True`.
- `SECURE_HSTS_SECONDS=63072000`.

## 8. Ordre recommande sur Hostinger

1. Pointer DNS `e-shelle.com` et sous-domaines vers le VPS.
2. Pousser le code Git propre avec migrations.
3. Lancer `sudo bash deploy.sh`.
4. Editer `/home/eshelle/app/.env`.
5. Lancer `python manage.py migrate`.
6. Lancer `python manage.py collectstatic --noinput`.
7. Creer le superuser.
8. Tester `nginx -t`.
9. Redemarrer `eshelle`.
10. Tester le site, admin, images, fiche business, Phone OCR, SEO agent, WhatsApp en dry-run.

## 9. Tests locaux realises

- Check Django: OK.
- Migrations dry-run: OK.
- Collectstatic dry-run: OK avec avertissements de conflits statiques non bloquants.
- Phone OCR: dependance Python ajoutee, Tesseract requis cote systeme.
- WhatsApp: securise en dry-run tant que Meta n'est pas configure.

## 10. Points a surveiller avant mise en ligne

- Les nouveaux fichiers non suivis par Git doivent etre ajoutes.
- Les migrations `business`, `whatsapp_agent`, `phone_ocr_agent`, `seo_agent` doivent etre incluses.
- Les images de demo et produits doivent exister dans `media/`.
- Les cles API ne doivent jamais etre commitees.
- La vraie cle `DJANGO_SECRET_KEY` doit remplacer la cle de demo.
- Si envoi WhatsApp reel: garder les preuves de consentement clients et commencer avec de petits volumes.
