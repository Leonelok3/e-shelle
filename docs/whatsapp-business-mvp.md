# WhatsApp Business E-Shelle — premier pilote

Le tableau de bord WhatsApp est relié à une fiche `BusinessProfile` :

- `/whatsapp-commerce/business/<id>/` affiche l’état de la connexion et l’inbox privée ;
- le parcours Meta utilise Embedded Signup v4, échange le code à usage unique côté serveur,
  enregistre le numéro avec le PIN 2 étapes et abonne le WABA aux webhooks ;
- les contacts et messages sont rattachés à leur fiche Business ; les numéros peuvent être
  présents chez plusieurs entreprises, mais les identifiants WABA et numéro sont uniques ;
- les réponses directes de ce premier pilote sont limitées à la fenêtre de service WhatsApp
  de 24 heures ouverte par le client. Les campagnes et relances automatisées ne sont pas
  activées dans cette tranche.
- Pro donne accès à la connexion et au CRM de contacts ; Business et Premium ajoutent
  la synchronisation des articles du catalogue Business vers le catalogue du WABA connecté.
- le CRM conserve les contacts après expiration, mais l’accès et l’envoi de réponses sont
  suspendus tant qu’une formule éligible n’est pas active ; les données ne sont pas supprimées.
- les articles WhatsApp doivent avoir un prix numérique en XAF et une image publique HTTPS.
  Un article déjà synchronisé est conservé comme indisponible dans Meta quand il est retiré
  de la fiche E-Shelle.
- Business et Premium peuvent planifier une relance individuelle par modèle approuvé. Le
  propriétaire doit attester et tracer le consentement explicite du client ; les messages
  entrants seuls ne valent pas consentement marketing. STOP désinscrit le contact et annule
  ses relances en attente.
- le moteur n’envoie ni campagnes de masse, ni texte libre planifié : les paramètres et
  l’approbation du modèle sont revérifiés à l’envoi. Une erreur n’est pas relancée
  automatiquement, afin d’éviter un doublon si l’acceptation Meta était incertaine. Le
  worker traite au plus dix relances arrivées à échéance par minute.

## Configuration Meta côté serveur

Ne jamais placer les secrets dans le HTML, le JavaScript ou Git. Configurer dans
l’environnement de déploiement :

```text
WHATSAPP_TECH_PROVIDER_APP_ID=
WHATSAPP_TECH_PROVIDER_APP_SECRET=
WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID=
WHATSAPP_GRAPH_API_VERSION=v25.0
WHATSAPP_APP_SECRET=
WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=False
```

`WHATSAPP_APP_SECRET` doit être le secret de la même application Meta dont le webhook
est configuré sur `/whatsapp/webhook/`. Ajouter le domaine HTTPS de production aux
domaines autorisés du Login for Business. La configuration Embedded Signup doit être
en v4. Avant d’ouvrir l’onboarding client, Meta doit avoir validé l’entreprise,
l’App Review et l’accès avancé requis. Le callback du webhook doit être abonné au champ
`account_update` et aux événements de messagerie nécessaires.

Les entreprises clientes possèdent leurs actifs WhatsApp et doivent ajouter leur propre
moyen de paiement Meta. L’abonnement E-Shelle ne règle pas les frais de conversations
Meta. La configuration de l’intégration ne rend pas le statut Tech Provider effectif :
seule l’approbation de Meta le fait.

## Déploiement

Le module `whatsapp_commerce` a été ajouté aux applications Django. Avant de déployer,
appliquer la migration additive :

```powershell
.\.venv\Scripts\python.exe manage.py migrate whatsapp_commerce
```

`WHATSAPP_COMMERCE_ENABLED` reste désactivé par défaut afin de ne pas activer les anciens
signaux de catalogue/rappels lors du déploiement. Ne l’activer qu’après avoir vérifié le
parcours public Boutique séparément et validé les modèles Meta de rappel. L’onboarding
et l’inbox business restent contrôlés par l’authentification du propriétaire, les droits
de la formule active et l’état de connexion individuel. La synchronisation Business utilise
le jeton et le WABA de la fiche concernée ; elle échoue explicitement si Meta ne retourne
pas un catalogue unique et ne retombe jamais sur les identifiants globaux de l’ancienne boutique.

Les relances Business sont protégées par leur propre drapeau, `WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED`,
désactivé par défaut. Leur planification reste impossible et les messages en attente sont annulés
par le poller lorsqu’il constate que ce drapeau est désactivé. Avant toute activation en production,
confirmer les permissions Meta de gestion et d’envoi, configurer un worker Celery et Celery Beat,
tester avec une fiche et un contact de test ayant un consentement réel, et vérifier les statuts de
livraison par webhook. La relance planifiée est une demande d’envoi à Meta ; la livraison n’est
confirmée que par les notifications de statut.

Vérification sans appel réel à Meta :

```powershell
.\.venv\Scripts\python.exe manage.py test whatsapp_commerce --noinput
```

Les tests remplacent les appels Graph API. Le mode réel ne doit pas être activé pour
valider les tests ou les captures d’écran de l’App Review.
