# Publication des annonces immobilières depuis WhatsApp

## Parcours

1. Le worker écoute uniquement le groupe désigné dans `TARGET_GROUP_NAME`.
2. Les messages et photos sont envoyés à l'API interne comme brouillons. Rien n'est publié automatiquement.
3. Un membre du staff contrôle et enregistre la vérification des informations dans **Immobilier → Annonces WhatsApp à valider**.
4. Il corrige les données manquantes, puis confirme qu'il a l'autorisation de republication des détails, photos et coordonnées.
5. La validation publie la fiche sur E-Shelle et tente ensuite son partage sur la page Facebook configurée.

Le parseur ne vérifie pas les faits : il propose un type ou une ville lorsqu'il reconnaît des mots-clés ou un quartier, mais ne complète pas volontairement un prix absent. L'opérateur doit confirmer toutes les informations avant publication. Le numéro de téléphone est masqué dans la description générée et n'est diffusé comme contact que si l'autorisation est confirmée.

Le worker traite les nouveaux messages reçus après sa connexion ; il ne récupère pas l'historique déjà présent dans WhatsApp. Pour commencer immédiatement avec une annonce existante, utiliser **Importer un message WhatsApp** dans le tableau des brouillons et ajouter le texte ainsi que les photos manuellement.

## Préparation en production

1. Informer les membres du groupe que les annonces et les photos peuvent être examinées en vue d'une republication. Obtenir l'accord du propriétaire ou du démarcheur pour les photos, le texte et le numéro de contact avant de confirmer l'autorisation dans l'interface.
2. Générer un secret aléatoire sur le serveur, sans le mettre dans Git :

   ```bash
   openssl rand -hex 32
   ```

3. Renseigner la même valeur dans l'environnement privé de Django (`INTERNAL_WHATSAPP_SECRET`) et dans le fichier `.env` privé du worker. Ce fichier ne doit pas être partagé ni committé. L'API répond `503` si le secret serveur n'est pas configuré; le worker refuse de démarrer si son secret ou le nom du groupe est absent.
4. Copier `immobilier_cameroun/worker_whatsapp_listener/.env.example` vers `.env` et configurer au minimum :

   ```dotenv
   DJANGO_INGEST_URL=https://e-shelle.com/immobilier/api/internal-ingest/
   INTERNAL_WHATSAPP_SECRET=<même secret aléatoire que Django>
   TARGET_GROUP_NAME=E-Shelle Immobilier
   ```

   Le nom du groupe est comparé exactement après retrait des espaces, signes et emojis décoratifs. Les emojis peuvent donc rester dans le vrai nom du groupe. Remplacer le domaine de l'URL seulement si l'installation utilise une autre adresse accessible depuis le worker.
5. Dans le répertoire `immobilier_cameroun/worker_whatsapp_listener`, installer les dépendances Node déclarées dans `package.json`, puis démarrer le worker avec `npm start`. Sur le VPS, le faire tourner dans un service supervisé sous l'utilisateur de l'application. Le répertoire `auth_info_baileys` contient la session WhatsApp : limiter ses permissions au compte de service et ne jamais le committer.
6. Associer uniquement le compte WhatsApp autorisé au worker et vérifier dans ses journaux qu'il indique le groupe exact attendu.
7. Configurer le jeton d'accès de la page Meta/Facebook via la configuration privée déjà utilisée par `get_facebook_page_credentials()`. Sans jeton valide, les fiches restent publiées sur E-Shelle et le partage Facebook échoue; le tableau des brouillons indique si un identifiant de publication Facebook a été enregistré.
8. Appliquer la migration Django avant de démarrer la nouvelle version :

   ```bash
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py check
   ```

## Premier test conseillé

Utiliser d'abord une annonce réelle dont le propriétaire a autorisé la republication. Vérifier le brouillon, son prix, la transaction, la ville, le quartier, les photos et le contact. Publier depuis le tableau de validation, puis ouvrir la fiche E-Shelle et la publication Facebook. Ne pas activer de publication automatique : le contrôle humain est volontaire.
