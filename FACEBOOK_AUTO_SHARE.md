# Guide d'Auto-Partage Facebook des Prestataires Premium — E-Shelle.com

Ce document détaille le fonctionnement, la configuration et l'exploitation du système de partage automatique des prestataires **PREMIUM** de **E-Shelle.com** vers la Page Facebook officielle **E-Shelle.com** (ID: `1316700031522892`).

---

## 1. Vue d'Ensemble & Architecture

- **Cible unique** : Publication exclusivement sur la Page Facebook officielle E-Shelle (aucune gestion de pages tierces de clients).
- **Déclencheur automatique** : Signal Django `post_save` sur `BusinessProfile` exécuté de manière asynchrone (thread non-bloquant).
- **Règles d'éligibilité (`should_share`)** :
  1. `is_premium = True` (`plan == BusinessProfile.Plan.PREMIUM`)
  2. `is_published = True` (`is_active = True` et `activation_status == ACTIVE`)
  3. Anti-doublon : non partagé au cours des dernières 24 heures (`facebook_shared_at is None` ou `> 24h`)
  4. Quota quotidien : maximum 3 publications par jour (`FACEBOOK_MAX_POSTS_PER_DAY = 3`)
- **Format du message AEO (Answer Engine Optimization)** :
  - Accroche géo-localisée : `🔥 NOUVEAU PREMIUM à {quartier}, {ville}!`
  - Fiche : Nom, Catégorie, Offre / Description courte, Prix indicatif
  - Contact direct : WhatsApp avec indicatif Cameroun `+237`
  - URL canonique indexable : `https://e-shelle.com/business/{slug}/`
  - Hashtags ciblés : `#EShelle #Cameroun #Premium #{Ville} #{Quartier} #{Categorie}`
- **Historique & Traçabilité** : Modèle `FacebookShareLog` avec statut, date, identifiant de post et message d'erreur éventuel.

---

## 2. Permissions Meta Requises

Pour publier au nom de la Page Facebook E-Shelle, l'application Meta et le token doivent disposer des autorisations suivantes :

1. `pages_manage_posts` : Permet à l'application de créer et publier des posts sur le flux de la Page.
2. `pages_read_engagement` : Permet de lire les statistiques, l'engagement et vérifier l'identité de la Page.
3. `pages_show_list` : Permet de lister les pages administrées par le compte utilisateur.

---

## 3. Comment Obtenir un Page Access Token Longue Durée (Permanent)

### Étape 1 : Obtenir un User Token court via Graph API Explorer
1. Rendez-vous sur [Meta for Developers Graph API Explorer](https://developers.facebook.com/tools/explorer/).
2. Sélectionnez votre **Meta App** (App ID: `1841260056892991`).
3. Dans **User or Page**, sélectionnez `User Token`.
4. Ajoutez les permissions : `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`.
5. Cliquez sur **Generate Access Token** et acceptez les autorisations Meta.

### Étape 2 : Échanger contre un User Token longue durée (60 jours)
Exécutez la requête HTTP suivante (ou utilisez le bouton "Inspect" puis "Extend Access Token" dans l'outil Access Token Debugger) :
```bash
curl -X GET "https://graph.facebook.com/v25.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=1841260056892991&\
client_secret=VOTRE_APP_SECRET&\
fb_exchange_token=VOTRE_USER_TOKEN_COURT"
```
Vous obtiendrez un token utilisateur valide 60 jours.

### Étape 3 : Récupérer le Page Access Token permanent
Avec le token utilisateur longue durée obtenu, interrogez la liste de vos comptes :
```bash
curl -X GET "https://graph.facebook.com/v25.0/me/accounts?access_token=USER_TOKEN_LONGUE_DUREE"
```
Dans la réponse JSON :
1. Repérez l'objet où `"id": "1316700031522892"` (Page E-Shelle.com).
2. Copiez la valeur du champ `"access_token"`.
> **Important** : Le Page Access Token généré à partir d'un User Token longue durée est **permanent** (sans date d'expiration), tant que le mot de passe de l'administrateur Meta n'est pas modifié.

---

## 4. Configuration des Variables d'Environnement (.env)

Ajoutez les variables suivantes dans votre fichier `.env` de production :

```ini
# ── Page Facebook Officielle E-Shelle ──────────────────────────────
FACEBOOK_PAGE_ID=1316700031522892
FACEBOOK_PAGE_ACCESS_TOKEN=EAAxxxxxxx...
FACEBOOK_MAX_POSTS_PER_DAY=3
FACEBOOK_AUTO_SHARE_ENABLED=True

# ── Meta App (pour les signatures et vérifications) ────────────────
FACEBOOK_APP_ID=1841260056892991
FACEBOOK_APP_SECRET=votre_app_secret_meta
```

---

## 5. Comment Tester en Mode Dry-Run

Le service fournit un paramètre `dry_run=True` permettant de tester l'intégralité de la logique de construction de message, de validation et de formatage sans envoyer de requête HTTP à Meta.

### Dans un terminal Django shell (`python manage.py shell`) :
```python
from business.models import BusinessProfile
from core.services.facebook_auto_share import (
    should_share,
    build_aeo_message,
    share_premium_to_facebook_page,
)

# Récupérer un profil test ou créer une instance en mémoire
biz = BusinessProfile.objects.filter(plan="premium", is_active=True).first()

if biz:
    # 1. Vérifier si le profil est éligible au partage
    print("Eligible :", should_share(biz))

    # 2. Prévisualiser le message optimisé AEO
    print("\n--- Message AEO ---")
    print(build_aeo_message(biz))

    # 3. Tester la publication en Dry-Run (ne contacte pas Facebook)
    post_id = share_premium_to_facebook_page(biz, dry_run=True)
    print("\nPost ID simulé :", post_id)
```

---

## 6. Suivi & Dashboard

Dans le tableau de bord de l'Agent SEO (`/seo/`), le bloc **Signalétique IA & Moteurs Génératifs (GEO / AEO)** affiche en temps réel :
- Le quota quotidien consommé : `Partage Facebook Premium: X/3 aujourd'hui`
- La dernière fiche partagée et l'ancienneté du partage : `Dernier: NomDuBusiness il y a X minutes`

Toutes les tentatives de partage sont également consultables dans l'interface d'administration Django sous **Profils Business > Logs Partages Facebook**.

---

## 7. Commande de Test de Non-Régression

Pour s'assurer que le système d'auto-partage ne dégrade aucun signal SEO, sitemap ou robots.txt :
```bash
python manage.py test seo_agent.tests -v2
```
Résultat attendu : **16 tests réussis avec succès**.
