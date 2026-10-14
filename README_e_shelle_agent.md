# Agent vendeur WhatsApp E-Shelle

L’agent est une extension de `whatsapp_commerce`. Le callback Django existant
`/whatsapp/webhook/` est conservé : il vérifie toujours le challenge Meta et la
signature `X-Hub-Signature-256`, puis transmet les événements au routage par WABA
et numéro déjà en place. ShellBot et les routes historiques `/whatsapp/` et
`/api/whatsapp/` restent séparés.

## Activation progressive

1. Déployer et appliquer les migrations :

   ```powershell
   .\.venv\Scripts\python.exe manage.py migrate
   ```

2. Configurer l’application Meta, sa signature webhook, l’onboarding Embedded
   Signup, les clés IA existantes et les permissions validées. Aucun secret ne
   doit être ajouté au dépôt ou au HTML.
3. Le drapeau serveur `WHATSAPP_COMMERCE_AI_ENABLED` est activé par défaut,
   mais chaque connexion commence avec `agent_enabled=False`. Le propriétaire
   doit ouvrir le tableau de bord de sa fiche, connecter un WABA actif, puis
   activer l’agent et sélectionner les articles à mettre en avant.
4. `WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED` active le worker globalement, tandis
   que `automations_enabled=False` par connexion maintient les relances arrêtées
   jusqu’à activation explicite dans le tableau de bord. En production, garder
   ce drapeau serveur à `True` seulement si Celery et Celery Beat sont actifs et
   que les modèles Meta sont approuvés. Les relances planifiées vérifient à nouveau l’abonnement, le
   consentement, le statut STOP et l’approbation du modèle avant chaque envoi.
5. Pour activer la cadence automatique, définir les variables d’environnement
   `WHATSAPP_COMMERCE_FOLLOW_UP_J1_TEMPLATE`,
   `WHATSAPP_COMMERCE_FOLLOW_UP_J3_TEMPLATE` et
   `WHATSAPP_COMMERCE_FOLLOW_UP_J7_TEMPLATE` avec les noms exacts des modèles
   français approuvés pour chaque WABA. Chaque modèle configuré doit contenir
   un bouton de réponse rapide intitulé `STOP`; sinon la relance est ignorée et
   journalisée. Une réponse entrante annule les relances précédentes. Le worker
   crée J+1/J+3/J+7 uniquement si le consentement marketing explicite est actif.

L’inbox est accessible sur `GET /whatsapp-commerce/inbox/`; la page liste
uniquement les fiches appartenant au compte connecté. Choisir une fiche ouvre son
tableau de bord `GET /whatsapp-commerce/business/<business_id>/`, qui contient
les conversations. Si une seule fiche a un WABA actif, la route inbox y redirige.

## Développement local sans Docker

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Pour le worker et Beat, dans deux consoles et avec un broker Redis disponible :

```powershell
.\.venv\Scripts\python.exe -m celery -A edu_cm worker --loglevel=INFO
.\.venv\Scripts\python.exe -m celery -A edu_cm beat --loglevel=INFO
```

Celery Beat contient déjà une tâche WhatsApp exécutée chaque minute; elle
respecte le drapeau serveur et le drapeau d’automatisation de chaque connexion.

Sans Redis, l’application et ses vues restent utilisables localement; les tâches
planifiées ne s’exécutent pas. `shellbot/docker-compose.yml` reste le compose
standalone de ShellBot, non requis pour Django.

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py test whatsapp_commerce --noinput
```

Les tests doivent mocker les appels à Meta et au LLM; ils ne doivent pas envoyer
de vrais messages.

## Limites de sécurité à conserver

- Les réponses libres passent uniquement par la fenêtre WhatsApp de 24 heures.
- Une relance hors fenêtre exige le consentement marketing explicite et un
  modèle approuvé par Meta pour le WABA du prestataire. STOP annule les relances.
- Les cadences J+1/J+3/J+7 nécessitent les noms des modèles approuvés et un bouton
  `STOP` tels que décrits ci-dessus. Les abandons de panier/vue, les remises
  automatiques, l’envoi de médias produits et le suivi après-vente ne sont pas
  activés par cette extension : ils nécessitent des déclencheurs et un rattachement
  de données propres au tenant.
- Une intention de commande/paiement produit une `pending_action` d’audit avec
  `status="pending_approval"`. Le guard vérifie le consentement, l’appartenance
  active de l’article au catalogue business et la fenêtre de 24 h ou la présence
  d’un modèle Meta approuvé. Même si le guard passe, aucune commande ni transaction
  n’est créée automatiquement : les modèles de boutique/paiement actuels exigent
  des identifiants et relations qui ne sont pas fournis par un contact WhatsApp.
- L’agent n’initie pas de commande payée, de paiement Mobile Money ou de rendez-vous
  sans identité/produit/créneau et confirmation adaptés. Les schémas actuels
  `boutique.Commande`, `payments.Transaction` et `salonhub.Appointment` ne
  représentent pas encore un checkout anonyme rattaché à une fiche Business.
- Une commission affiliée ne peut être créée qu’à partir d’une transaction
  complétée et d’un referral/compte affilié éligible; le calcul ne doit pas être
  anticipé au moment d’une simple intention WhatsApp.
- Les statuts des modèles Meta sont journalisés à partir de
  `message_template_status_update`; ils ne remplacent pas la validation Meta en
  temps réel avant programmation/envoi.
- `*.pem` est déjà ignoré par `.gitignore`, mais cela ne retire pas une clé déjà
  suivie par Git. Le fichier de clé de production doit être révoqué/rotaté, puis
  retiré de l’historique Git par une procédure d’incident coordonnée. Ne pas
  afficher ni recopier son contenu.
