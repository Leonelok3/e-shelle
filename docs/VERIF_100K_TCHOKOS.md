# Vérification E-Shelle — 100k Tchokos

Date : 22 octobre 2026  
Branche observée : `feature/100k-tchokos`

## Résultat

Revue statique réalisée sans lecture de `.env`, sans connexion au VPS et sans changement applicatif. Le test d’intégration SQLite et l’exécution des tests Django n’ont pas pu être faits : l’interpréteur disponible est Python 3.14.4 et Django n’y est pas installé (`ModuleNotFoundError`). Aucun package n’a été installé.

| Module | Statut | Preuve fichier:ligne |
|---|---|---|
| Modèle Business + champs catalogue | Présents | `business/models.py:15`, `business/models.py:330`, `business/models.py:348-355` |
| Migration catalogue (gros, SKU, stock) | Présente | `business/migrations/0034_businesscatalogitem_wholesale_fields.py:18-40` |
| Contact global WhatsApp et consentement | Présents | `whatsapp_agent/models.py:5-29` |
| Campagne Business | Présente, liée à Business | `whatsapp_agent/models.py:57-83` |
| Lignes MessageEnvoi en attente et contact PME | Présentes | `whatsapp_agent/models.py:192-228` |
| Modèle contact privé PME et consentement | Présents, associés au business | `whatsapp_commerce/models.py:66-105` |
| Historique des messages WhatsApp PME | Présent | `whatsapp_commerce/models.py:129` |
| Consentement `consent_marketing` | Migration 0015 présente | `whatsapp_agent/migrations/0015_add_consent_fields_safe.py:27` |
| Backfill consentement et type de campagne | Migration 0016 présente | `whatsapp_agent/migrations/0016_campaign_consent_type_and_backfill.py:6-23` |
| Liaison MessageEnvoi → contact PME | Migration 0018 présente | `whatsapp_agent/migrations/0018_messageenvoi_business_contact.py:1-18` |
| Import catalogue CSV | Code présent; exécution SQLite non vérifiée | `business/catalog_import.py:39`, `business/catalog_import.py:99-112`; test existant `business/tests_catalog_import.py:23` |
| Préparation campagne PME | Parcours statiquement cloisonné et construit avec `business_contact` | `whatsapp_agent/views.py:140-170`; statut par défaut `whatsapp_agent/models.py:195-228` |
| Contrôle d’entreprise et consentement avant envoi | Contrôle présent | `whatsapp_commerce/campaigns.py:108-115` |
| WABA et historique de campagne PME | Historique écrit dans les messages Business; chemin PME n’appelle pas le journal global | `whatsapp_commerce/campaigns.py:193`; `whatsapp_agent/tasks.py:90-91`, `whatsapp_agent/tasks.py:165-166` |
| Webhook protégé | Non modifié durant cette vérification | `whatsapp_agent/views.py:1113` |
| `whatsapp_agent/services.py` | Non modifié durant cette vérification | Fichier absent du diff de cette session |
| Fichiers modèles demandés | Liste confirmée | `business/models.py:15`, `whatsapp_commerce/models.py:66`, `whatsapp_agent/models.py:5` |
| Tests campagne: cohérence des règles d’audience | À revoir : tests legacy encore orientés audience globale | `whatsapp_agent/tests_business_campaigns.py:509`, `whatsapp_agent/tests_business_campaigns.py:810` |
| Git / branche | Branche `feature/100k-tchokos`; changements préexistants présents | `git status --short --branch` et `git diff --stat` observés pendant la vérification |
| `templates/home.html` | Changement préexistant préservé; non édité ici | `git diff --numstat`: 50 ajouts, 22 suppressions; `git status`: déjà modifié |
| Push | Non effectué; attente de validation manuelle | Aucun push exécuté |

## Contrôle CSV demandé

L’import n’a pas été exécuté contre une base SQLite, faute de Django installé. Le code accepte les colonnes `sku, nom, prix_detail, prix_gros, stock, categorie`, valide les montants/quantités et crée ou met à jour par SKU sans supprimer les lignes absentes. Les cas ciment à 4 850 FCFA, tôles et carreaux 60×60 à 8 500 FCFA devront être confirmés par exécution locale des tests dès qu’un environnement Django est disponible.

## État Git et périmètre

Au début de la revue, la branche était `feature/100k-tchokos`; `git diff --stat` indiquait 18 fichiers suivis modifiés (628 insertions, 98 suppressions), et plusieurs nouveaux fichiers non suivis, dont les migrations, l’import catalogue et `whatsapp_commerce/campaigns.py`. `templates/home.html` était déjà modifié. Ce rapport est le seul fichier ajouté par cette vérification. Aucun fichier applicatif, migration, webhook, `.env` ou service n’a été édité. Aucun VPS n’a été contacté et aucun push n’a été réalisé.

## Point à résoudre avant validation

Les tests `test_staff_campaign_form_explains_global_audience` et `test_staff_campaign_creation_keeps_global_campaigns_available` semblent conserver l’attente d’un mode d’audience globale, alors que le parcours PME est désormais strictement limité aux contacts de l’entreprise. Comme Django n’est pas disponible ici, leur résultat runtime et l’intention produit exacte restent à confirmer avant le push.
