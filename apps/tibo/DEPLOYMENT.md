# Déploiement TIBO

TIBO est prêt pour VPS Ubuntu avec Nginx, Gunicorn, PostgreSQL, Redis, Cloudflare et HTTPS.

## Checklist

- Configurer `DATABASE_URL` PostgreSQL.
- Configurer `CELERY_BROKER_URL=redis://localhost:6379/0`.
- Ajouter les variables `TIBO_*` dans `.env`.
- Exécuter `python manage.py collectstatic`.
- Planifier les tâches Celery Beat `tibo.sync_shopify_products` et `tibo.sync_amazon_prices`.
- Activer HTTPS, HSTS, sauvegardes PostgreSQL et monitoring erreurs.

