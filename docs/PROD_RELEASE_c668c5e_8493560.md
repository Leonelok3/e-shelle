# Préparation de release — E-Shelle 100k + 3 expériences

**Source :** `feature/100k-tchokos` (`8493560`, précédé de `c668c5e`)  
**Cible envisagée :** `main`  
**État :** vérifications locales terminées; merge, push, tag et déploiement non exécutés.

## Résultats locaux

- `git status --short` était vide sur `feature/100k-tchokos`.
- Les commits récents sont `8493560` puis `c668c5e`; la comparaison avec `origin/main` contient les changements de la fonctionnalité.
- Tests ciblés combinés : **73/73 réussis en 46,468 s**.
- `makemigrations --check --dry-run` : `No changes detected`.
- `py_compile` réussi pour `business/catalog_import.py`, `whatsapp_commerce/campaigns.py`, `njangi/models.py` et `business/models.py`.
- Aucun diff de `HEAD~1` dans `whatsapp_agent/services.py` ni `whatsapp_agent/views.py`; la vue `webhook_meta` est toujours présente à `whatsapp_agent/views.py:1117`.
- Les documents de déploiement/specification ne contiennent pas de valeur de secret détectée. La checklist de déploiement nomme toutefois les variables de secret requises, sans en donner les valeurs.
- Aucune référence à `vps3581805` dans le code applicatif; aucun accès réseau au VPS n’a été tenté.

Le contrôle `check --deploy` local a remonté les avertissements attendus pour `SECURE_SSL_REDIRECT=False` (utilisé pour les tests) et la `SECRET_KEY` locale. Ce résultat ne valide pas la configuration de production; il faudra refaire le contrôle dans l’environnement de déploiement après vérification de sa configuration sécurisée.

## Migrations à appliquer

| Application | Migration |
|---|---|
| `business` | `0034_businesscatalogitem_wholesale_fields` |
| `business` | `0035_businessprofile_language` |
| `njangi` | `0019_njangiachatgroupe_njangiachatparticipation_and_more` |
| `whatsapp_agent` | `0016_campaign_consent_type_and_backfill` |
| `whatsapp_agent` | `0018_messageenvoi_business_contact` |
| `whatsapp_commerce` | `0007_businesswhatsappmessage_language` |

`whatsapp_agent.0015_add_consent_fields_safe` est déjà dans l’historique du projet et doit aussi être appliquée si l’environnement cible ne l’a pas encore marquée comme appliquée. L’ordre et les dépendances Django sont gérés par `manage.py migrate`.

## Configuration

Les quatre variables ci-dessous sont lues par le code. Vérifier les valeurs dans la configuration de production, sans les copier dans Git ni les afficher dans les journaux :

```text
WHATSAPP_COMMERCE_ENABLED=true
WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=true
WHATSAPP_DRY_RUN=false
WHATSAPP_COMMERCE_AI_ENABLED=true
```

`WHATSAPP_CONFIG_READY` est calculé par les settings et dépend des identifiants Meta requis; confirmer son état vrai au moyen de l’écran de santé sans afficher les secrets. La configuration réelle de Meta, des WABA par entreprise, du stockage image et du fournisseur vocal n’a pas été vérifiée ici.

Les variables suggérées dans le prompt `BUSINESS_CATALOG_PHOTO_UPLOAD_ENABLED`, `NJANGI_GROUP_BUYING_ENABLED` et `WHATSAPP_NJANGI_MARKETING_TEMPLATE_NAME` ne sont pas lues par les settings/code actuels. Les ajouter seules n’activera pas ces parcours. Le parcours Njangi ignore actuellement les invitations hors fenêtre de 24 h; un modèle marketing approuvé et une implémentation de son usage sont nécessaires avant de les envoyer.

## Commandes de publication à exécuter manuellement

Après revue de cette checklist et autorisation de publication, depuis un terminal local avec le dépôt à jour :

```powershell
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git merge --no-ff feature/100k-tchokos -m "release: 100k Tchokos + 3 magies mondiales - 73 tests verts - vocal pidgin, photo catalog, njangi commerce"
git push origin main
git tag v100k-tchokos-73tests-3magies
git push origin v100k-tchokos-73tests-3magies
```

Ces commandes n’ont pas été lancées. Le tag doit être créé après validation du merge et des contrôles CI/revue de `main`.

## Vérifications de déploiement et rollback

Sur le VPS, manuellement et après autorisation, appliquer les migrations, lancer `manage.py check --deploy`, collecter les statiques, redémarrer les services puis exécuter les smoke tests sans envoyer de vrai message WhatsApp. Ne pas activer les envois réels avant d’avoir confirmé les identifiants Meta et le WABA de chaque entreprise.

En cas de rollback applicatif après un merge, identifier le commit de merge et l’annuler avec `git revert -m 1 <merge_commit>`; ne pas réécrire l’historique publié. Les migrations déjà appliquées et les données créées ne sont pas annulées par ce revert de code : établir une procédure de retour DB distincte avant toute opération de schéma.

## Contrôles post-déploiement à faire manuellement

- Confirmer migrations appliquées, `check --deploy` sans avertissements de sécurité non résolus et `/health/` ou `/admin/` en HTTP 200.
- Contrôler catalogue/photo, langue Business et progression Njangi avec des données de test autorisées.
- Confirmer qu’un vocal crée un `VoiceOverJob`; ne pas envoyer un vrai vocal tant que le fournisseur vocal n’est pas configuré et validé.
- Surveiller les journaux et vérifier l’absence de répétition anormale des avertissements de relance/catalogue.
- Faire relire les textes Ewondo et Bassa par un locuteur natif avant usage commercial.
