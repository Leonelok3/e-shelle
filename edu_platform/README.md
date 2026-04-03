# EduCam Pro — Plateforme E-Learning

Application Django modulaire intégrée dans e-shelle.com.
Sujets d'examens · Corrections officielles · Vidéos de cours
Paiement Orange Money & MTN MoMo · Cameroun (FCFA)

---

## Installation dans e-shelle

### 1. Ajouter dans `INSTALLED_APPS`

```python
"edu_platform.apps.EduPlatformConfig",
```

### 2. Ajouter le middleware dans `MIDDLEWARE`

```python
"edu_platform.middleware.device_lock_middleware.DeviceLockMiddleware",
```

### 3. Ajouter les URLs dans `edu_cm/urls.py`

```python
path("edu/", include("edu_platform.urls", namespace="edu")),
```

### 4. Ajouter la configuration dans `settings.py`

```python
EDU_PLATFORM = {
    'SITE_NAME': 'EduCam Pro',
    'ORANGE_MONEY_API_KEY':      os.getenv('ORANGE_MONEY_API_KEY', ''),
    'ORANGE_MONEY_API_SECRET':   os.getenv('ORANGE_MONEY_API_SECRET', ''),
    'ORANGE_MONEY_MERCHANT_KEY': os.getenv('ORANGE_MONEY_MERCHANT_KEY', ''),
    'MTN_MOMO_SUBSCRIPTION_KEY': os.getenv('MTN_MOMO_SUBSCRIPTION_KEY', ''),
    'MTN_MOMO_API_USER':         os.getenv('MTN_MOMO_API_USER', ''),
    'MTN_MOMO_API_KEY':          os.getenv('MTN_MOMO_API_KEY', ''),
    'MTN_MOMO_ENVIRONMENT':      os.getenv('MTN_MOMO_ENVIRONMENT', 'sandbox'),
    'WEBHOOK_HMAC_SECRET':       os.getenv('EDU_WEBHOOK_HMAC_SECRET', ''),
}
SITE_URL = os.getenv('SITE_URL', 'https://e-shelle.com')
```

### 5. Variables d'environnement (`.env`)

Voir `.env.example` pour la liste complète.

### 6. Migrations et fixtures

```bash
python manage.py migrate edu_platform
python manage.py loaddata edu_platform/fixtures/plans.json
python manage.py loaddata edu_platform/fixtures/subjects_sample.json
```

### 7. Cron quotidien

```bash
# Expire les abonnements terminés (à ajouter dans crontab)
0 2 * * * /path/to/venv/bin/python manage.py cleanup_expired_subscriptions
```

---

## Commandes de gestion

```bash
# Générer un code de test (DEBUG seulement)
python manage.py generate_test_code --plan-id 1

# Exporter les abonnés actifs en CSV
python manage.py export_subscribers > abonnes.csv

# Nettoyer les abonnements expirés
python manage.py cleanup_expired_subscriptions
```

---

## Tests

```bash
python manage.py test edu_platform
# 21 tests — tous doivent passer
```

---

## URLs disponibles

| URL | Description |
|-----|-------------|
| `/edu/` | Landing page |
| `/edu/plans/` | Forfaits |
| `/edu/register/` | Inscription |
| `/edu/login/` | Connexion |
| `/edu/activate/` | Activer un code |
| `/edu/dashboard/` | Espace étudiant |
| `/edu/subjects/` | Liste des matières |
| `/edu/admin/` | Back-office admin |
| `/edu/webhooks/orange-money/` | Webhook Orange Money |
| `/edu/webhooks/mtn-momo/` | Callback MTN MoMo |

---

## Détachement en standalone (~30 min)

1. Créer un nouveau projet Django : `django-admin startproject educam_standalone`
2. Copier le répertoire `edu_platform/` dans le nouveau projet
3. Copier la config `EDU_PLATFORM` dans le nouveau `settings.py`
4. Ajouter `edu_platform` dans `INSTALLED_APPS`
5. Configurer `AUTH_USER_MODEL` (ou utiliser le User Django par défaut)
6. Ajouter les URLs : `path('edu/', include('edu_platform.urls', namespace='edu'))`
7. Copier les variables d'environnement depuis `.env.example`
8. `python manage.py migrate && python manage.py loaddata edu_platform/fixtures/plans.json`
9. `python manage.py createsuperuser`

---

## Architecture sécurité

- **Device Binding** : 1 code = 1 seul appareil (fingerprint SHA-256 composite)
- **Webhooks** : Vérification HMAC-SHA256 (Orange Money) et status check (MTN)
- **PDF** : Servi via token signé (15 min) sans URL directe
- **Vidéos** : Token signé + désactivation clic droit
- **Rate limiting** : À configurer via nginx ou django-ratelimit
