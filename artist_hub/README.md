# Artist Hub — Casting gratuit OPLUS

Application Django de candidature pour la Douala Fashion Week 2026.
Le casting est gratuit pour le Cameroun et l’international.

Le candidat complète ses informations, les consentements, deux photos et une
vidéo de présentation. Son inscription est confirmée sans transaction. Il reçoit
un numéro, un code d’accès et une fiche PDF. Le jury gère les présélections,
les retenus et les refus depuis le tableau de bord staff.

## Installation

Ajouter `artist_hub.apps.ArtistHubConfig` à `INSTALLED_APPS` et inclure
`artist_hub.urls` avec le namespace `artist_hub`. Dépendances : Django, Pillow,
ReportLab et qrcode. Les relations utilisateur utilisent `settings.AUTH_USER_MODEL`.

```bash
python manage.py migrate
python manage.py init_casting_session --extend-registration
python manage.py collectstatic --noinput
```

La clôture est fixée au 13 novembre 2026 à 23:59:59, heure de Douala.
Les migrations confirment les anciens dossiers en attente et conservent les
décisions du jury. Les anciens enregistrements financiers restent conservés ;
aucune route publique de paiement n’est activée.

Déploiement du VPS existant : `docs/artist-hub-production.md`.

```bash
python manage.py test artist_hub.tests --settings=artist_hub.tests.settings --noinput
```

Casting : 14 novembre 2026. Défilé : 26 décembre 2026.
