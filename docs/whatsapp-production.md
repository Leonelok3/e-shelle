# E-Shelle - WhatsApp reel en production

## Diagnostic et correctif du 19 septembre 2026

Le diagnostic local constate `WHATSAPP_DRY_RUN=True`, sans token ni Phone Number ID. Cela ne permet pas de conclure sur la configuration du site en ligne. L'accès SSH configuré a refusé l'authentification ; aucun message réel ni lancement de campagne n'a été effectué pendant cet audit.

Le bouton de test conserve maintenant les commandes `template:nom`, permet de choisir explicitement un modèle, sa langue et ses paramètres de corps (liste JSON). `hello_world` utilise `en_US` et aucun paramètre. Un modèle personnalisé doit utiliser le nom exact approuvé dans Meta : vérifier notamment `deutsch_space_decouvert` visible sur la capture, alors que la valeur locale est `deutsch_space_decouverte`. Le modèle immigration visible sur la capture est encore « In review ».

Les tests sont enregistrés séparément des destinataires de campagne. L'acceptation HTTP n'est plus présentée comme une livraison : les webhooks signés mettent à jour le suivi et conservent les erreurs asynchrones, par exemple 131047. La page de campagne affiche les cinq derniers tests et leurs erreurs. Actualiser la page pour suivre la livraison. Les messages de campagne en attente ne sont pas relancés automatiquement par ce correctif.

Avant déploiement de ce correctif, appliquer la migration additive `whatsapp_agent.0009_whatsapp_test_delivery` selon la procédure du projet. Elle crée uniquement la table de suivi des tests. Cette migration n'a pas été appliquée à la production pendant l'audit.

Diagnostic serveur en lecture seule, sans affichage des secrets :

```bash
python manage.py check_whatsapp_delivery --campaign-id 25 --check-meta --check-workers
# Ajouter --waba-id IDENTIFIANT_DU_COMPTE_WHATSAPP pour vérifier les noms, langues et statuts des modèles.
```

Un worker qui ne répond pas est un indice, pas une preuve absolue d'arrêt (inspection désactivée ou réseau possible). Ne pas redémarrer les consommateurs ni relancer une campagne avant d'avoir contrôlé les messages déjà dans la file : cela pourrait envoyer les destinataires en attente.

Validation locale : 10 tests automatiques de soumission, modèles, paramètres, simulation, accès staff, signatures et statuts asynchrones ; `manage.py check` réussi. Aucun appel Meta dans ces tests.

```powershell
.\.venv\Scripts\python.exe manage.py test whatsapp_agent.tests_delivery --settings=whatsapp_agent.test_settings --noinput
```

Référence : [Meta — notifications de statut](https://www.postman.com/meta/whatsapp-business-platform/request/rgtfq23/message-status-update-notifications). La réception d'un identifiant de message ne prouve pas sa livraison au téléphone.

Ce guide sert a passer du mode simulation au vrai envoi via l'API officielle Meta WhatsApp Cloud API.

## 1. Prerequis Meta

- Compte Meta Business.
- App Meta Developer avec le produit WhatsApp active.
- WhatsApp Business Account.
- Phone Number ID.
- Access token Meta valide.
- Verify token choisi par toi pour le webhook E-Shelle.

Pour un premier test, Meta fournit souvent un numero de test et un token temporaire. Pour la production, utilise un token permanent de System User.

## 2. Variables a mettre sur Railway ou VPS

```env
WHATSAPP_DRY_RUN=False
WHATSAPP_TOKEN=EAAB...
WHATSAPP_PHONE_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=un_secret_que_tu_choisis
WHATSAPP_API_URL=https://graph.facebook.com/v19.0/123456789012345/messages
```

Si `WHATSAPP_API_URL` n'est pas defini, Django le construit automatiquement depuis `WHATSAPP_PHONE_ID`.

## 3. Webhook Meta

URL callback a donner a Meta:

```text
https://ton-domaine.com/whatsapp/webhook/
```

Verify token:

```text
la valeur de WHATSAPP_VERIFY_TOKEN
```

## 4. Test reel prudent

1. Mets `WHATSAPP_DRY_RUN=False`.
2. Redemarre l'application.
3. Ouvre une campagne.
4. Mets ton numero dans "Envoyer un test a mon numero".
5. Clique "Envoyer le test".

Le test direct ne depend pas de Celery. C'est le meilleur premier controle.

## 5. Envoi massif

Pour l'envoi massif reel, ajoute Redis et Celery:

```env
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
```

Sans Redis/Celery, garde le mode simulation pour les tests locaux.

## 6. Important

WhatsApp/Meta limite les messages commerciaux. Pour contacter un prospect hors conversation recente, il faut normalement utiliser des templates WhatsApp approuves par Meta. Le texte libre marche surtout dans une fenetre de conversation ouverte par le client.
