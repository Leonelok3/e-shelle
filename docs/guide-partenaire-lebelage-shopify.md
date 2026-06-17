# Guide partenaire - Systeme LEBELAGE vers Shopify

Ce guide explique comment utiliser le systeme E-Shelle pour exporter des produits LEBELAGE en local, exporter les produits d'une boutique Shopify en local, verifier les fichiers, puis preparer une importation propre.

Lien local de l'interface:

```text
http://127.0.0.1:8000/lebelage-importer/
```

## 1. Ce que fait le systeme

Le systeme permet de:

- scraper les produits du site LEBELAGE;
- exporter les produits en local dans un fichier JSON;
- exporter les produits en local dans un fichier CSV;
- afficher les produits extraits dans une interface web locale;
- exporter les produits deja presents dans une boutique Shopify;
- comparer avant toute importation.

Important: l'interface actuelle ne cree pas et ne modifie pas de produit Shopify. Elle sert d'abord au controle local.

## 2. Peut-on utiliser le systeme pour plusieurs boutiques Shopify?

Oui.

Le principe est simple: une boutique Shopify = une configuration Shopify.

Pour chaque boutique, il faut:

- son domaine Shopify, par exemple `ma-boutique.myshopify.com`;
- son token Admin API;
- les permissions API necessaires;
- un dossier ou des fichiers d'export separes pour eviter les melanges.

Le systeme peut donc servir pour:

- ta propre boutique;
- une boutique client;
- plusieurs boutiques de partenaires;
- des boutiques de test avant production.

## 3. Workflow recommande

Toujours travailler dans cet ordre:

1. Exporter les produits LEBELAGE en local.
2. Ouvrir le fichier CSV et verifier les titres, prix, images et descriptions.
3. Exporter les produits actuels de la boutique Shopify en local.
4. Comparer les produits LEBELAGE avec les produits Shopify existants.
5. Decider ce qu'il faut importer, modifier ou ignorer.
6. Importer seulement apres validation humaine.

Ce workflow evite les doublons, les mauvais prix et les produits envoyes trop vite.

## 4. Exporter LEBELAGE en local

Depuis l'interface:

```text
http://127.0.0.1:8000/lebelage-importer/
```

Cliquer sur:

```text
Exporter LEBELAGE en local
```

Fichiers generes:

```text
tmp/lebelage_products.json
tmp/lebelage_products.csv
```

Depuis le terminal:

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --limit 10 --max-pages 1
```

Pour exporter plus de produits:

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --limit 50 --max-pages 5
```

## 5. Exporter une boutique Shopify en local

Avant d'exporter une boutique Shopify, configurer les variables:

```powershell
$env:SHOPIFY_SHOP_DOMAIN="ma-boutique.myshopify.com"
$env:SHOPIFY_ADMIN_ACCESS_TOKEN="shpat_xxxxxxxxx"
$env:SHOPIFY_API_VERSION="2026-01"
```

Depuis l'interface:

```text
http://127.0.0.1:8000/lebelage-importer/
```

Cliquer sur:

```text
Exporter ma boutique Shopify
```

Fichiers generes:

```text
tmp/shopify_products.json
tmp/shopify_products.csv
```

Depuis le terminal:

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --export-shopify
```

## 6. Gerer plusieurs boutiques

Pour plusieurs boutiques, il faut changer les variables Shopify avant chaque export.

Exemple boutique 1:

```powershell
$env:SHOPIFY_SHOP_DOMAIN="boutique-a.myshopify.com"
$env:SHOPIFY_ADMIN_ACCESS_TOKEN="token_boutique_a"
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --export-shopify --shopify-out tmp/shopify_boutique_a.json --shopify-csv tmp/shopify_boutique_a.csv
```

Exemple boutique 2:

```powershell
$env:SHOPIFY_SHOP_DOMAIN="boutique-b.myshopify.com"
$env:SHOPIFY_ADMIN_ACCESS_TOKEN="token_boutique_b"
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --export-shopify --shopify-out tmp/shopify_boutique_b.json --shopify-csv tmp/shopify_boutique_b.csv
```

Bonne pratique:

- ne pas melanger les exports de plusieurs clients;
- creer un sous-dossier par client;
- noter la date de chaque export;
- ne jamais partager le token d'un client avec un autre client.

## 7. Peut-on donner le systeme sur une cle USB?

Oui, mais il faut faire attention.

Tu peux mettre sur la cle USB:

- le dossier du projet;
- le script `tools/lebelage_shopify_agent.py`;
- l'interface `lebelage_importer/`;
- les fichiers de documentation;
- un fichier `.env.example`;
- les instructions d'installation.

Ne jamais mettre sur la cle USB:

- ton fichier `.env` reel;
- les tokens Shopify;
- les mots de passe;
- les exports clients sensibles;
- les informations de paiement.

Pour un partenaire, donne plutot:

```text
e_shelle/
  docs/
  tools/
  lebelage_importer/
  requirements.txt
  manage.py
  .env.example
```

Le partenaire devra mettre ses propres identifiants Shopify.

## 8. Installation chez un partenaire

Sur le PC du partenaire:

1. Installer Python.
2. Copier le dossier du projet.
3. Ouvrir PowerShell dans le dossier.
4. Creer l'environnement virtuel si besoin:

```powershell
python -m venv .venv
```

5. Activer l'environnement:

```powershell
.\.venv\Scripts\Activate.ps1
```

6. Installer les dependances:

```powershell
pip install -r requirements.txt
```

7. Lancer Django:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

8. Ouvrir:

```text
http://127.0.0.1:8000/lebelage-importer/
```

## 9. Permissions Shopify necessaires

Pour exporter les produits Shopify, il faut au minimum:

```text
read_products
```

Pour importer ou modifier des produits plus tard, il faudra:

```text
write_products
```

Shopify explique que les access scopes controlent ce qu'une app peut lire ou modifier, par exemple `read_products` et `write_products`.

Sources officielles:

- https://shopify.dev/docs/api/admin-graphql/2026-01/objects/AccessScope
- https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin

## 10. Controle avant import

Avant d'importer quoi que ce soit, verifier:

- nom du produit;
- prix;
- image principale;
- description;
- tags;
- doublons;
- marge commerciale;
- frais de livraison;
- taxes;
- conformite cosmetique du pays de vente;
- droit d'utiliser les images fournisseur.

## 11. Ameliorations recommandees

Certaines ameliorations sont maintenant integrees au systeme:

- comparateur LEBELAGE vs Shopify;
- detection nouveaux produits, doublons et prix differents;
- calcul automatique du prix final;
- descriptions vendeuses locales;
- import Shopify en brouillon.

### Fonctions integrees

Calcul de marge:

```text
prix final = prix source + livraison + marge
```

Comparateur:

```text
tmp/lebelage_shopify_comparison.json
tmp/lebelage_shopify_comparison.csv
```

Import securise:

```text
Les produits sont crees avec le statut draft.
Ils ne sont pas publies automatiquement.
```

Guide PDF:

```text
docs/guide_utilisation_lebelage_shopify.pdf
```

Voici les prochaines ameliorations pour rendre le systeme encore plus professionnel.

### A. Profils multi-boutiques

Ajouter une page pour enregistrer plusieurs boutiques:

- nom du client;
- domaine Shopify;
- token chiffre;
- devise;
- pays;
- statut actif/inactif.

Avantage: plus besoin de changer les variables PowerShell manuellement.

### B. Nettoyage IA avance des descriptions

Ajouter un agent IA connecte a une API qui transforme la description fournisseur en fiche produit vendeuse:

- titre court;
- description client;
- benefices;
- conseils d'utilisation;
- avertissement;
- FAQ.

### C. Detection automatique des categories

Classer les produits automatiquement:

- serum;
- ampoule;
- cream;
- toner;
- cleanser;
- set;
- mask.

### D. Journal d'activite

Garder un historique:

- date d'export;
- boutique concernee;
- nombre de produits;
- erreurs;
- fichier genere;
- utilisateur.

### E. Mode partenaire

Prevoir une version vendable:

- logo du partenaire;
- page d'accueil simple;
- guide integre;
- bouton d'export;
- bouton de comparaison;
- aucun acces au reste d'E-Shelle.

### F. Protection des tokens

Chiffrer les tokens Shopify ou les stocker hors du dossier partage.

Avantage: tu peux vendre le systeme sans risque de fuite de credentials.

### G. Planification automatique

Ajouter un bouton ou une tache planifiee:

- export chaque matin;
- detection des nouveaux produits;
- rapport email;
- notification WhatsApp.

## 12. Offre commerciale possible

Tu peux vendre ce systeme comme:

```text
Pack Import Produit Shopify
```

Contenu du pack:

- installation locale;
- configuration boutique;
- export fournisseur;
- export boutique Shopify;
- comparaison;
- import controle;
- formation du partenaire;
- support mensuel.

Prix possible selon le client:

- installation simple;
- installation + formation;
- installation + automatisation;
- abonnement maintenance mensuel.

## 13. Positionnement simple

Phrase commerciale:

```text
Je vous installe un systeme local qui extrait les produits fournisseur, les controle, les compare avec votre boutique Shopify et prepare l'import sans risque de doublons.
```

Ce positionnement est clair, vendable et rassurant pour les entreprises.
