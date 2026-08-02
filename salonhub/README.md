# SalonHub — SaaS de réservation pour salons de coiffure & instituts de beauté

Un SaaS complet en **Python / Django** qui permet à des salons de coiffure et
instituts de beauté de créer leur vitrine en ligne, et à leurs clients de
trouver un établissement, consulter les créneaux libres et **prendre
rendez-vous directement sur WhatsApp**, sans appel téléphonique.

Pensé pour être déployé en sous-domaine de **e-shelle.com**
(ex : `beaute.e-shelle.com`).

---

## 1. Ce que fait le SaaS

### Côté client
- Recherche de salons par ville, quartier, nom ou type de prestation
- Fiche établissement : photos, description, prestations et tarifs, horaires
- Sélecteur de date (14 prochains jours) + créneaux horaires disponibles
  calculés en temps réel (horaires d'ouverture − rendez-vous déjà pris)
- Réservation en 3 clics : prestation → créneau → coordonnées, puis
  **redirection automatique vers WhatsApp** avec un message pré-rempli
  contenant tous les détails du rendez-vous

### Côté prestataire (salon / institut)
- Compte "prestataire" séparé du compte client
- Espace pro (`/espace-pro/`) : statistiques (RDV du jour, de la semaine,
  en attente), liste des demandes de rendez-vous, changement de statut
  (en attente / confirmé / annulé / terminé)
- Gestion des établissements, prestations et horaires via l'admin Django
  (accessible uniquement sur ses propres établissements)
- Chaque réservation client est **enregistrée en base ET envoyée sur
  WhatsApp** : aucune demande n'est perdue, même si le client ne finalise
  pas l'envoi du message.

---

## 2. Stack technique

- Django 6 (compatible Django 5.x)
- Base de données : SQLite par défaut (facilement remplaçable par
  PostgreSQL en production, recommandé)
- Aucun framework JS : HTML/CSS/JS natif (léger, rapide, facile à maintenir)
- Design système "maison" (pas de Bootstrap/Tailwind) dans
  `static/css/style.css` — identité visuelle "ticket de rendez-vous",
  encre café / or bruni / ivoire, typographies Fraunces + Manrope

---

## 3. Structure du projet

```
salonhub/
├── config/              # settings, urls racine
├── accounts/            # utilisateur custom (client / prestataire)
├── salons/               # établissements, catégories, prestations, horaires
│   └── management/commands/seed_demo.py   # jeu de données de démo
├── bookings/             # rendez-vous, calcul des créneaux, lien WhatsApp
├── dashboard/             # espace pro (statistiques + gestion des RDV)
├── templates/             # tous les gabarits HTML (design premium)
├── static/css/style.css   # design system complet
├── requirements.txt
└── manage.py
```

### Le cœur du système : `bookings/utils.py`
- `get_available_slots(salon, date, service)` : génère les créneaux libres
  d'une journée à partir des horaires d'ouverture du salon, en retirant les
  créneaux déjà réservés et les horaires passés si la date est aujourd'hui.
- `build_whatsapp_link(salon, appointment)` : construit l'URL
  `https://wa.me/<numero>?text=...` avec un message prêt à envoyer.

---

## 4. Installation locale (VS Code)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo        # crée un salon de démonstration
python manage.py createsuperuser  # pour accéder à /admin/

python manage.py runserver
```

Puis ouvrez :
- `http://127.0.0.1:8000/` → page d'accueil
- `http://127.0.0.1:8000/s/eclat-de-reine-yaounde/` → salon de démo
- `http://127.0.0.1:8000/admin/` → administration
- `http://127.0.0.1:8000/espace-pro/` → espace pro
  (connectez-vous avec `demo_owner` / `demo1234`)

---

## 5. Ajouter un salon (mode manuel, avant automatisation)

1. Le prestataire crée un compte via **"Ajouter mon salon"**
   (`/compte/devenir-partenaire/`)
2. Il est redirigé vers son **espace pro**, avec un lien pour ajouter son
   établissement dans l'admin (`/admin/salons/salon/add/`)
3. Il renseigne : nom, ville, quartier, **numéro WhatsApp** (obligatoire,
   format international sans espaces, ex : `237690000000`), logo, photo de
   couverture, prestations (nom, prix, durée) et horaires d'ouverture par
   jour de la semaine.
4. Dès que `is_active = True`, l'établissement apparaît sur la plateforme.

> Idée d'évolution rapide : remplacer l'admin Django par un vrai formulaire
> "Mon salon / Mes prestations / Mes horaires" dans `dashboard/`, en
> réutilisant les mêmes modèles. La structure le permet déjà.

---

## 6. Déploiement en sous-domaine de e-shelle.com

1. **DNS** : créer un enregistrement `CNAME` ou `A` pour
   `beaute.e-shelle.com` (ou le nom choisi) pointant vers votre serveur.
2. Dans `config/settings.py`, `ALLOWED_HOSTS` contient déjà `.e-shelle.com`
   (couvre tous les sous-domaines). Ajustez si besoin.
3. Variables d'environnement recommandées en production :
   ```
   SECRET_KEY=une-cle-secrete-longue-et-aleatoire
   DEBUG=False
   ```
4. Base de données : remplacez SQLite par PostgreSQL
   (`pip install psycopg2-binary` + `DATABASES` dans `settings.py`).
5. Fichiers statiques : `python manage.py collectstatic`, puis servez
   `staticfiles/` via Nginx ou WhiteNoise.
6. Serveur d'application : `gunicorn config.wsgi:application` derrière
   Nginx (certificat SSL via Let's Encrypt / Certbot).
7. Médias (logos, photos) : en production, préférez un stockage S3-compatible
   plutôt que le disque local.

### Personnalisation par salon
Le projet est déjà multi-établissements (un seul déploiement sert tous les
salons, chacun avec sa propre fiche `/s/<slug>/`). Si vous souhaitez à terme
un **sous-domaine dédié par salon** (ex : `eclat-de-reine.e-shelle.com`),
la structure de données (modèle `Salon` avec `slug`) le permet : il suffira
d'ajouter un middleware qui résout le sous-domaine vers le bon salon.

---

## 7. Prochaines étapes suggérées

- Formulaire self-service pour que le prestataire gère lui-même ses
  prestations/horaires sans passer par l'admin Django
- Notation et avis clients
- Envoi d'un rappel automatique par WhatsApp (via l'API Business WhatsApp,
  au-delà du simple lien `wa.me`) la veille du rendez-vous
- Paiement d'acompte en ligne (Mobile Money / Orange Money / carte)
- Application mobile ou PWA pour les prestataires

---

**Identifiants de démonstration**
- Prestataire : `demo_owner` / `demo1234`
- Salon de démo : Éclat de Reine — Bastos, Yaoundé
