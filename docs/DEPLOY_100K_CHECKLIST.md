# Checklist de déploiement — 100k Tchokos

Cette checklist prépare le déploiement. Elle ne change aucune configuration distante et ne valide pas à elle seule la connexion Meta ou les secrets.

## Variables d’environnement

Confirmer ces valeurs dans l’environnement de déploiement, sans les copier dans Git :

```text
WHATSAPP_COMMERCE_ENABLED=true
WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=true
WHATSAPP_DRY_RUN=false
WHATSAPP_COMMERCE_AI_ENABLED=true
```

`WHATSAPP_CONFIG_READY` est calculé au démarrage dans `edu_cm/settings.py`. Le contrôle doit retourner vrai lorsque `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN` et `WHATSAPP_APP_SECRET` sont tous renseignés. Ne pas afficher ni enregistrer les valeurs de ces variables dans les journaux.

Avec `DATABASE_URL` configuré, `WHATSAPP_DRY_RUN` doit être désactivé; sinon les settings lèvent `ImproperlyConfigured`.

## Avant mise en production

- [ ] Vérifier les quatre indicateurs ci-dessus dans la configuration du service.
- [ ] Vérifier `WHATSAPP_CONFIG_READY=True` dans l’écran de santé WhatsApp.
- [ ] Vérifier que les secrets Meta sont définis dans le gestionnaire de secrets du déploiement, jamais dans le dépôt.
- [ ] Appliquer les migrations Django et vérifier qu’elles sont marquées appliquées :
  - [ ] `business.0034_businesscatalogitem_wholesale_fields`
  - [ ] `whatsapp_agent.0015_add_consent_fields_safe`
  - [ ] `whatsapp_agent.0016_campaign_consent_type_and_backfill`
  - [ ] `whatsapp_agent.0018_messageenvoi_business_contact`
- [ ] Vérifier séparément la connexion WABA active de chaque PME et lancer une campagne contrôlée avec consentement.
- [ ] Importer le CSV Tchokos dans le profil Business cible et contrôler SKU, prix et stock.

## Vérification locale de ce changement

- `whatsapp_agent.tests_business_campaigns`: 27 tests réussis.
- `business.tests_catalog_import`: 5 tests réussis, dont un CSV de dix produits comprenant ciment à 4 850 FCFA, carreaux 60×60 à 8 500 FCFA et tôles.
- Aucun test local ne prouve la configuration effective du VPS; cette checklist doit être confirmée depuis son panneau de déploiement après autorisation.
