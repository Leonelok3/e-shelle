# 🌟 ARTIST HUB — Application Django Modulaire & Portable

Application Django autonome conçue pour artistes et organisateurs d'événements culturels/mode.
Développée initialement pour **GROUP OPUS** dans le cadre du casting officiel de la **Douala Fashion Week 2026** (26 décembre 2026, Hôtel Krystal Palace Douala).

---

## 🚀 Portabilité & Indépendance Totale

Cette application a été conçue pour être **100 % autonome** :
* **Zéro dépendance envers les modèles ou templates d'e_shelle** : Utilise `settings.AUTH_USER_MODEL` pour toutes les relations d'utilisateurs.
* **Templates & Statics isolés** : Thème sombre haute couture autonome dans `artist_hub/templates/artist_hub/` et CSS/JS dans `artist_hub/static/artist_hub/`.
* **Configuration centralisée** : Tout est piloté depuis `artist_hub/conf.py` via `settings.ARTIST_HUB = {...}` ou des variables d'environnement (`.env`).
* **Migrations incluses** : Dossier de migrations dédié `artist_hub/migrations/`.

---

## 📦 Procédure d'extraction vers un projet Django séparé

Pour déployer `artist_hub` sur le domaine personnel du client (ex: `https://group-opus.com`) :

### 1. Copier le dossier
Copiez l'intégralité du dossier `artist_hub/` à la racine de votre nouveau projet Django.

### 2. Dépendances requises (`requirements.txt`)
Assurez-vous que les packages suivants sont installés :
```bash
pip install Django>=5.0 Pillow reportlab qrcode requests python-dotenv
```

### 3. Déclaration dans `settings.py`
Ajoutez l'application à vos `INSTALLED_APPS` :
```python
INSTALLED_APPS = [
    # Applications Django standard...
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # ARTIST HUB
    "artist_hub.apps.ArtistHubConfig",
]

# Modèle Utilisateur personnalisé ou standard
AUTH_USER_MODEL = "auth.User"  # ou votre CustomUser

# Configuration optionnelle de personnalisation
ARTIST_HUB = {
    "ARTIST_NAME": "GROUP OPUS",
    "BRAND_NAME": "OPLUS",
    "EVENT_TITLE": "Douala Fashion Week 2026",
    "PRIMARY_COLOR": "#D4AF37",       # Or haute couture
    "ACTIVE_PAYMENT_PROVIDER": "manual_proof",  # ou "mock", "notchpay"
    "FEE_CAMEROON": 3000,
    "FEE_INTERNATIONAL": 5000,
    "ORANGE_MONEY_NUMBER": "+237 695 487 796",
    "MTN_MOMO_NUMBER": "+237 675 293 836",
    "ECOBANK_RIB": "4020789949967166",
}
```

### 4. Configuration des URLs (`urls.py`)
Intégrez les routes racines avec le namespace obligatoire :
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # Rendre artist_hub accessible à la racine ou sur un sous-chemin
    path("", include("artist_hub.urls", namespace="artist_hub")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 5. Exécution des migrations & initialisation
```bash
python manage.py migrate
python manage.py init_casting_session
python manage.py createsuperuser
python manage.py runserver
```

---

## 🧩 Architecture des Modules

```text
artist_hub/
├── conf.py               # Configuration & thématique dynamique
├── urls.py               # Routes modulaires
├── admin.py              # Administration Django personnalisée
├── payments/             # Module de paiement partagé (GenericForeignKey)
│   ├── models.py         # Modèle Payment (UUID, preuve, idempotence)
│   ├── signals.py        # Signaux payment_succeeded, payment_failed
│   ├── services.py       # Traitement atomique et vérification serveur
│   ├── views.py          # Webhook CSRF exempt, polling et simulateur
│   └── providers/        # Abstraction : Mock, ManualProof, NotchPay
├── casting/              # Module Casting (Phase 1)
│   ├── models.py         # CastingSession, Candidate, CandidatePhoto
│   ├── forms.py          # Formulaire 4 étapes, règles mineurs, honeypot
│   ├── services.py       # Numérotation auto, code d'accès, ReportLab PDF
│   ├── views.py          # Inscription publique, suivi candidat, streaming PDF
│   ├── views_dashboard.py# Dashboard staff (KPIs, filtres, export CSV)
│   └── signals.py        # Validation automatique de la candidature
├── ticketing/            # Squelette billetterie avec QR codes (Phase 2)
└── booking/              # Squelette réservations / devis (Phase 3)
```

---

## 🔒 Sécurité & Idempotence
* **Idempotence des paiements** : La méthode `handle_payment_success` garantit qu'un paiement ne peut être validé deux fois, protégeant contre les doublons de webhooks.
* **Validation serveur** : Ne fait jamais confiance au navigateur client. Le webhook et le polling interrogent toujours directement l'état serveur.
* **Gestion des mineurs** : Si le candidat a moins de 18 ans, les champs tuteur, téléphone et accord parental deviennent obligatoires.
* **Protection anti-spam** : Champ honeypot et validation MIME stricte (Pillow).

---

## 📞 Support & Contacts Officiels
* **Production** : OPLUS / GROUP OPUS
* **WhatsApp** : +237 675 293 836
* **Email** : oplusproduction9@gmail.com
* **Lieu** : Hôtel Krystal Palace, Douala, Cameroun
