# E-Shelle Resto — Guide d'installation et d'utilisation

Plateforme de découverte de restaurants et de menus au Cameroun.  
Module Django intégré à E-Shelle.com, accessible via `/resto/`.

---

## Prérequis

- Python 3.11+
- Django 5.x
- Pillow (traitement d'images)
- PostgreSQL (production) ou SQLite (développement)

---

## Installation rapide

### 1. Installer Pillow (si pas déjà fait)

```bash
pip install Pillow
```

Ou dans `requirements.txt`, vérifier la présence de :
```
Pillow>=10.0.0
```

---

## Agent WhatsApp E-Shelle

Le module `whatsapp_agent` permet de creer des campagnes WhatsApp et d'envoyer des messages en masse via l'API officielle Meta WhatsApp Business.

### Variables `.env`

```bash
WHATSAPP_TOKEN=EAAxxxxx
WHATSAPP_PHONE_ID=123456789
WHATSAPP_VERIFY_TOKEN=mon_secret_webhook
ANTHROPIC_API_KEY=sk-ant-xxxxx
WHATSAPP_DRY_RUN=True
```

### Commandes de lancement

```bash
pip install -r requirements.txt
python manage.py makemigrations accounts whatsapp_agent
python manage.py migrate
python manage.py seed_whatsapp_contacts
redis-server
celery -A edu_cm worker -l info
celery -A edu_cm beat -l info
python manage.py runserver
```

Dashboard: `/whatsapp/campagnes/`

---

## Agent Commercial IA E-Shelle

Le module `commercial_agent` sert a suivre les prospects, generer des messages commerciaux IA, relancer sur WhatsApp et transformer les prestataires en abonnements.

```bash
python manage.py makemigrations commercial_agent
python manage.py migrate
python manage.py seed_commercial_agent
```

Dashboard staff: `/commercial-agent/`

### Passage en envoi reel Meta

1. Cree une app Meta sur `developers.facebook.com` et active WhatsApp Business.
2. Copie le Bearer token dans `WHATSAPP_TOKEN`.
3. Copie l'ID du numero Business dans `WHATSAPP_PHONE_ID`.
4. Configure le webhook Meta vers `/whatsapp/webhook/`.
5. Mets le meme secret dans Meta et dans `WHATSAPP_VERIFY_TOKEN`.
6. Quand un test avec ton propre numero est OK, passe `WHATSAPP_DRY_RUN=False`.

Tant que `WHATSAPP_DRY_RUN=True`, aucune requete d'envoi n'est faite a Meta.

### 2. Vérifier les paramètres (settings.py)

Ces lignes ont été ajoutées automatiquement :

```python
INSTALLED_APPS = [
    ...
    "resto.apps.RestoConfig",  # ✅
]

TEMPLATES = [{
    ...
    "context_processors": [
        ...
        "resto.context_processors.resto_globals",  # ✅
    ],
}]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

RESTO_FREE_TRIAL_DAYS = 30  # ✅
```

### 3. Vérifier les URLs (urls.py)

```python
path("resto/", include("resto.urls", namespace="resto")),  # ✅
```

### 4. Créer les migrations et migrer

```bash
python manage.py makemigrations resto
python manage.py migrate
```

### 5. Peupler la base avec des données de démo

```bash
python manage.py seed_resto
```

Pour réinitialiser les données avant de repeupler :
```bash
python manage.py seed_resto --reset
```

**Données créées :**
- 6 villes camerounaises (Yaoundé, Douala, Bafoussam, Bamenda, Garoua, Kribi)
- 26 quartiers réels
- 7 catégories alimentaires (cuisine camerounaise, grillades, etc.)
- 5 restaurants avec 30+ plats authentiques
- 1 compte propriétaire de démo : `demo@eshelle-resto.cm` / `Demo@Resto2026`

### 6. Lancer le serveur de développement

```bash
python manage.py runserver
```

Accéder à : [http://localhost:8000/resto/](http://localhost:8000/resto/)

---

## Structure des URLs

| URL | Vue | Description |
|-----|-----|-------------|
| `/resto/` | HomeView | Page d'accueil |
| `/resto/restaurants/` | RestaurantListView | Liste + filtres |
| `/resto/r/<slug>/` | RestaurantDetailView | Détail restaurant + menu |
| `/resto/recherche/` | SearchView | Recherche HTMX |
| `/resto/inscription/` | RestaurantRegisterView | Inscription restaurant |
| `/resto/track/` | TrackContactView | Suivi contacts (HTMX POST) |
| `/resto/dashboard/` | DashboardHomeView | Tableau de bord propriétaire |
| `/resto/dashboard/profil/` | DashboardProfileView | Édition profil |
| `/resto/dashboard/menu/` | DashboardMenuView | Gestion menu |
| `/resto/dashboard/analytics/` | DashboardAnalyticsView | Statistiques |
| `/resto/admin-panel/` | admin_dashboard | Panel admin (staff) |

---

## Fonctionnalités principales

### Côté client (public)
- 🔍 **Recherche HTMX** — sans rechargement de page
- 🗂️ **Filtres** — par ville, catégorie, statut (ouvert/fermé)
- 📱 **Mobile-first** — navigation bas de page, sticky CTA bar
- 💬 **WhatsApp** — liens wa.me pré-remplis en français
- 📞 **Appel direct** — liens `tel:` natifs
- ❤️ **Favoris** — sauvegarde restaurants (utilisateurs connectés)

### Côté restaurateur (dashboard)
- 📊 **Statistiques** — vues, appels, WhatsApp sur 7 jours (Chart.js)
- 🍽️ **Gestion menu** — CRUD catégories + plats avec HTMX
- ⚡ **Toggle disponibilité** — 3 états (disponible / dans X min / indisponible) sans rechargement
- 📝 **Profil** — photos avec aperçu instantané (Alpine.js)
- 🔄 **Toggle statut** — ouvert/fermé en un clic

### Côté admin (staff)
- ✅ **Approbation** — valider ou rejeter les restaurants
- ⭐ **Mise en avant** — sélection des restaurants vedettes
- 📈 **Aperçu stats** — contacts du jour, abonnements actifs

---

## Modèles de données

```
City → Neighborhood
FoodCategory (M2M avec Restaurant)
Restaurant → owner (User)
  └── Subscription (OneToOne)
  └── MenuCategory
       └── Dish
  └── ContactLog
  └── Favorite (M2M with User)
```

---

## Plans d'abonnement

| Plan | Durée | Description |
|------|-------|-------------|
| `free_trial` | 30 jours | Essai gratuit à l'inscription |
| `basic` | Variable | Plan de base |
| `premium` | Variable | Plan premium |

Le paiement se fait hors ligne (contact WhatsApp/téléphone).

---

## Technologies utilisées

| Technologie | Usage |
|-------------|-------|
| Django 5.x | Backend, ORM, templates |
| Tailwind CSS (CDN) | Styles — aucune étape de build |
| Alpine.js | Interactivité côté client |
| HTMX | Mises à jour partielles de page |
| Chart.js | Graphiques analytiques |
| PostgreSQL | Base de données (production) |
| Pillow | Traitement des images |

---

## Notes de sécurité

- Toutes les vues dashboard nécessitent `LoginRequiredMixin`
- Vérification de propriété (owner check) sur toutes les vues d'édition
- CSRF protégé sur tous les formulaires HTMX via le header `X-CSRFToken`
- ContactLog : seul le `session_key` et l'IP sont stockés (pas de données personnelles)
- Validation des images : max 5 Mo, formats JPG/PNG/WebP uniquement

---

## Performance (optimisé pour la 3G camerounaise)

- Toutes les images : `loading="lazy"`
- `select_related` et `prefetch_related` sur toutes les requêtes avec jointures
- Pagination : 12 restaurants par page
- Compteur de vues basé sur la session (1 vue par session et par restaurant)
- Pas de JavaScript bloquant (Alpine.js et HTMX chargés en `defer`)

---

## Contact & Support

WhatsApp : +237 680 625 082  
Site : [e-shelle.com/resto](https://e-shelle.com/resto)
