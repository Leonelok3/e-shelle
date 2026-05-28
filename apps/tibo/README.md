# TIBO

TIBO est une app Django modulaire de dropshipping premium pour le Canada.

## URLs

- Storefront: `/tibo/`
- API REST: `/api/tibo/`
- Dashboard staff: `/tibo/admin-dashboard/`

## Modules

- `models/`: catalogue, panier, commandes, paiements, affiliation.
- `services/`: panier, commandes, Stripe, PayPal, Shopify, Amazon.
- `api/`: endpoints DRF produits, catégories, panier, commandes, wishlist.
- `templates/tibo/`: UI premium isolée.
- `static/tibo/`: CSS, JS et assets TIBO.
- `management/commands/`: imports et synchronisations.

## Commandes

```bash
python manage.py makemigrations tibo
python manage.py migrate
python manage.py import_products --limit 50
python manage.py sync_shopify
python manage.py sync_amazon
python manage.py clear_old_data
```

## Variables

Copiez `apps/tibo/.env.example` dans votre `.env` principal et renseignez les clés réelles.

