# Déployer E-Shelle sur Render

Ce déploiement sert à obtenir rapidement un lien public de démonstration pendant que le VPS est en pause.

## Étapes

1. Pousse le projet sur GitHub.
2. Va sur Render, puis **New +** > **Blueprint**.
3. Connecte le dépôt GitHub E-Shelle.
4. Render détecte `render.yaml`.
5. Lance le déploiement.

Render va créer :

- un service web `eshelle-demo`,
- une base PostgreSQL gratuite `eshelle-demo-db`,
- les migrations Django,
- les données de démo principales.

## Variables importantes

Les variables de base sont déjà dans `render.yaml`. Après le premier déploiement, remplace si besoin :

- `SITE_URL` par l'URL réelle Render obtenue.
- `RUN_RENDER_SEED` à `false` après la première démonstration si tu ne veux plus reseeder à chaque build.
- `OPENAI_API_KEY` si tu veux tester les fonctions IA en ligne.

## Commande de démarrage

```bash
gunicorn edu_cm.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

## Limites de la version gratuite Render

- Le service peut dormir après inactivité.
- Les fichiers uploadés dans `media/` ne sont pas persistants comme sur un VPS.
- Pour les vraies photos produit en production, il faudra brancher un stockage externe comme Cloudinary, S3 ou un volume payant.
