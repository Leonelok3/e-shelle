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
4. `WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED` est désactivé par défaut. Garder ce
   drapeau serveur à `False` jusqu’au pilote; l’activation doit se faire
   entreprise par entreprise, avec modèles Meta approuvés, bouton STOP respecté
   et annulation des relances si le contact répond. Celery et Celery Beat doivent
   être actifs. Les relances vérifient à nouveau l’abonnement, le consentement,
   le statut STOP et l’approbation du modèle avant chaque envoi.
5. Pour activer la cadence automatique, définir les variables d’environnement
   `WHATSAPP_COMMERCE_FOLLOW_UP_J1_TEMPLATE`,
   `WHATSAPP_COMMERCE_FOLLOW_UP_J3_TEMPLATE` et
   `WHATSAPP_COMMERCE_FOLLOW_UP_J7_TEMPLATE` avec les noms exacts des modèles
   français approuvés pour chaque WABA. Chaque modèle configuré doit contenir
   un bouton de réponse rapide intitulé `STOP`; sinon la relance est ignorée et
   journalisée. Une réponse entrante annule les relances précédentes. Le worker
   crée J+1/J+3/J+7 uniquement si le consentement marketing explicite est actif.

## Commande WhatsApp confirmée

- Un premier message entrant crée `consent_service=True` pour le traitement de
  la demande, sans accorder le consentement marketing. Seul `OUI PUB` (ou
  l’enregistrement d’un accord marketing explicite dans le CRM) active
  `consent_marketing`.
- Si l’article actif du catalogue Business et son prix numérique sont
  identifiables, l’agent crée un brouillon et demande au client de vérifier
  l’article, la quantité, le total et la ville, puis de répondre `OUI`.
- Seule une confirmation explicite `OUI`, `OUI CONFIRME` ou le token UUID du
  brouillon crée une commande `source="whatsapp_confirmed"` et une ligne liée
  à l’article du catalogue. Une contrainte et une transaction atomique évitent
  les doublons par brouillon.
- Une transaction est créée en `pending_awaiting_manual_validation`; elle ne
  déclenche aucun paiement Mobile Money. Son lien est un contact WhatsApp du
  prestataire prérempli pour convenir du paiement, pas une passerelle de paiement.
  Le prestataire voit les brouillons, commandes et transactions à valider dans
  son Inbox Business.
- La commande ne peut être créée si l’article ou le prix ne sont pas validés,
  si le contact n’a pas initié la conversation, ou si l’article n’appartient pas
  au catalogue actif de cette fiche. Dans ces cas, la demande reste en attente
  d’intervention humaine.

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
- Le brouillon de commande ne devient une vraie commande qu’après la confirmation
  explicite du client décrite ci-dessus. Aucun paiement n’est initié automatiquement;
  le prestataire doit valider manuellement les modalités et réception du paiement.
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
  suivie par Git. La PEM doit être révoquée côté GCP; `.gitignore` seul ne suffit
  pas et ne retire pas une clé déjà suivie de Git ou de son historique. Ne pas
  afficher ni recopier son contenu.
