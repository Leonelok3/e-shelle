# E-Shelle - WhatsApp reel en production

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
