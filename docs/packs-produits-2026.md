# Audit produit E-Shelle et grille de packs — 8 octobre 2026

## Résumé exécutif

E-Shelle dispose déjà d'un large ensemble d'applications Django et d'un premier
parcours WhatsApp Business par fiche entreprise. Ce n'est toutefois pas encore un
SaaS multi-entreprises entièrement unifié avec paiement automatique, boutiques
illimitées et forfaits multi-applications.

Les constats déterminants pour les offres :

- Les prix déclarés par le seed après la modification locale du 8 octobre sont
  **0, 5 000, 15 000 et 25 000 XAF**. La commande seed n'a pas été lancée sur le
  VPS : sa base de production peut encore porter Business à 10 000 XAF jusqu'à
  l'exécution de la commande.
- Le plan Pro relie une fiche à un WABA et ouvre l'accès au CRM WhatsApp. Business
  et Premium ajoutent la synchronisation de catalogue et les relances individuelles
  par modèles Meta approuvés.
- Les limites connues du catalogue Business sont 5 articles en Gratuit, 20 en Pro,
  50 en Business et sans plafond déclaré en Premium. Elles ne prouvent pas que la
  Boutique digitale globale est une boutique SaaS séparée et illimitée pour chaque
  client.
- Un abonnement par fiche ne donne pas aujourd'hui un droit unifié aux applications
  Immobilier, Auto, Agro, Éducation et aux autres verticales. Les fonctions existent,
  mais le bundle multi-applications et sa facturation restent à concevoir.
- Le code de demande d'activation Business redirige le client vers WhatsApp pour
  validation. Les choix MTN MoMo et Orange Money existent dans le modèle de
  transaction, mais le parcours de vente des plans n'est pas un paiement opérateur
  automatique démontré par ce code.
- Les modèles ne définissent aucun quota mensuel de messages, aucun quota CRM de
  contacts ni aucun nombre de sièges d'équipe. Il ne faut pas vendre ces éléments
  comme des limites contractuelles implémentées.
- Selon la sortie VPS communiquée par le propriétaire, `whatsapp_commerce.0001` à
  `0004` ont été appliquées et le service `eshelle` est actif. Cet état serveur est
  rapporté d'après cette sortie, pas interrogé directement pendant cet audit.
- Le propriétaire indique que la candidature Meta est « In review » et anticipe
  une vérification le 13 octobre 2026. Une date d'approbation future ne peut pas
  être garantie : ne pas publier « Partenaire officiel », « vérifié » ou « premier
  Tech Provider » comme faits avant confirmation effective de Meta.

## Méthode et limites de vérification

Audit réalisé à partir du dépôt local propre sur `main`, commit `39a1205`, des
modèles, vues, tâches, configuration, migrations et documents présents. Les
fonctionnalités ci-dessous sont qualifiées d'après les surfaces de code trouvées,
pas d'après des ventes ou des utilisateurs de production.

Les éléments suivants n'ont pas pu être établis par le dépôt ou les extraits
fournis :

- les valeurs d'environnement actuellement configurées sur le VPS, notamment les
  drapeaux WhatsApp, secrets Meta, Redis et l'état réel des workers Celery ;
- l'approbation App Review/Tech Provider par Meta, les permissions avancées, la
  conformité de chaque modèle de message et la délivrabilité en production ;
- les lignes de plans actuellement présentes dans la base de production et la
  confirmation que la commande de seed y a été lancée ;
- le coût moyen réel par client (CPU, stockage privé, médias, sauvegardes, support,
  frais de paiement et coût variable des APIs).

Le fichier demandé `docs/tcr_ter_quality.ma` n'a pas été trouvé dans le dépôt.
`whatsapp-business-mvp.md`, `whatsapp-files-2026.md`, `whatsapp-production.md` et
`whatsapp-template-selector.md` existent. Ils décrivent plusieurs générations du
produit et ne doivent pas remplacer la lecture du code courant.

## Fonctionnalités WhatsApp réellement présentes

### Parcours WhatsApp Business par fiche — `whatsapp_commerce`

Les modèles et vues de `whatsapp_commerce/` contiennent :

- connexion Embedded Signup Meta côté serveur, échange du code, enregistrement du
  numéro, abonnement du WABA aux webhooks et conservation chiffrée du jeton ;
- une connexion WABA par `BusinessProfile` (relation `OneToOne`) et unicité du WABA
  et du Phone Number ID dans l'application ;
- import des contacts et messages entrants dans une inbox attachée à la fiche,
  statuts asynchrones des messages et vérification du propriétaire avant accès ;
- réponse texte individuelle seulement dans la fenêtre de service WhatsApp de
  24 heures ; en dehors de cette fenêtre, il faut un modèle Meta approuvé ;
- CRM contacts : nom, téléphone, étapes Nouveau/Ouvert/Qualifié/Gagné/Perdu, tags,
  notes, consentement, retrait/STOP et date de relance ;
- planification de relances individuelles utilisant un modèle et une langue
  actuellement approuvés par Meta, avec consentement marketing explicite vérifié
  au moment de la planification et de l'envoi ;
- annulation des relances en attente après désinscription, changement de connexion
  ou désactivation du drapeau d'automatisation ;
- réception des statuts de livraison dans le webhook. « Accepté par Meta » ne
  signifie pas « livré » ;
- synchronisation d'articles du catalogue Business vers le catalogue du WABA de
  cette fiche, sans bascule vers les identifiants globaux de la Boutique ;
- journalisation de visites de produits et clics WhatsApp. Un autre mécanisme de
  relance de panier abandonné existe, avec consentement et vérification d'achat,
  mais il utilise la configuration historique de Boutique : ce n'est pas la
  relance CRM tenant-local décrite plus haut.

### Droits du code et protections

`whatsapp_commerce/entitlements.py` réserve la connexion et le CRM à une fiche
active ayant Pro, Business ou Premium. La synchronisation du catalogue et la
relance individuelle sont réservées à Business et Premium. Après expiration, le
CRM reste en base, mais les actions protégées sont refusées.

Dans `edu_cm/settings.py`, les valeurs par défaut du code sont :

- `WHATSAPP_COMMERCE_ENABLED=False` ;
- `WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=False` ;
- `WHATSAPP_DRY_RUN=True` pour le parcours historique WhatsApp.

Une variable du VPS peut remplacer les défauts locaux : il faut vérifier
l'environnement réel avant toute affirmation de disponibilité. Le worker traite au
plus dix relances CRM arrivées à échéance par minute ; c'est un plafond de
traitement technique, **pas** un quota mensuel promis au client. Les frais de
conversation/modèle Meta ne sont pas inclus dans l'abonnement E-Shelle.

### Parcours WhatsApp historique — `whatsapp_agent`

Un second produit WhatsApp distinct comporte des contacts, campagnes, destinataires,
modèles, tests d'envoi, journal d'envoi, conversations/messages, pièces jointes,
suivi de statuts et appels. Des vues staff couvrent la création/lancement de
campagnes, sélection de modèles, réponses et historique. Le parcours de fichiers
gère des formats et limites de taille décrits dans `whatsapp-files-2026.md`.

Ce parcours historique n'est pas le CRM auto-service d'une entreprise : ses vues
sont protégées staff, il repose sur une configuration WhatsApp globale historique
et son mode réel n'a pas été confirmé sur le VPS. Ne pas annoncer que chaque
abonné dispose d'un accès aux campagnes de masse ou à ce centre opérateur.

### Marketing et automatisation

- Les campagnes CRM tenant-local de `whatsapp_commerce` sont des relances
  individuelles par modèle approuvé avec consentement. Le code exclut les campagnes
  de masse et le texte libre programmé.
- `check_abandoned_carts` sait chercher une vue de produit âgée de 30 minutes,
  non convertie et explicitement autorisée avant de tenter un rappel. La fonction
  est derrière `WHATSAPP_COMMERCE_ENABLED` et dépend de l'ancienne configuration
  produit : activation et opération réelle non confirmées.
- `adgen` enregistre des briefs de campagne et génère des contenus publicitaires
  (titres, bénéfices, textes Facebook/Instagram/WhatsApp, hashtags, scripts TikTok,
  voix et vidéo selon le parcours). Cela ne constitue pas une publication ou une
  campagne WhatsApp envoyée automatiquement à la clientèle.
- `facebook_agent` gère pages, règles/templates, publications immédiates ou
  planifiées, posts publiés, logs et statistiques. C'est une intégration Facebook,
  pas une fonctionnalité de WABA.
- `commercial_agent` stocke des prospects, scripts et relances et expose des
  fonctions staff de qualification, import et génération de messages. Il ne donne
  pas automatiquement ces sièges aux comptes clients.

## Boutique et fonctions transversales

### Fiche Business et catalogue autonome

`business.BusinessProfile` lie un propriétaire à une activité/module et porte le
plan, l'échéance, le numéro de contact, la fiche publique, les compteurs de vues,
clics et leads, les crédits IA et les boosts. Une fiche publique peut afficher des
produits, services, menus, livraisons et offres, images/vidéos, contact WhatsApp,
avis et mesures de performance. Des rapports et un kit de livraison IA existent
dans les vues du module.

Limites déclarées pour les articles de `BusinessCatalogItem` :

| Plan du code | Articles fiche Business | Photos supplémentaires / article |
|---|---:|---:|
| Gratuit | 5 | 0 |
| Pro | 20 | 2 |
| Business | 50 | 4 |
| Premium | Pas de plafond déclaré | 7 |

Les vues de gestion du catalogue utilisent ces limites. Ne pas confondre ces
articles avec les produits de `boutique.Produit`.

### Boutique digitale

`boutique` contient un catalogue de produits numériques, catégories, images, avis,
panier, lignes de panier, commandes, lignes de commande et accès/téléchargements.
Les vues montrent navigation, détail, panier, ajout/retrait, checkout et
téléchargement.

Le modèle `Produit` a un vendeur utilisateur facultatif, mais ne relie pas chaque
produit à un `BusinessProfile` ni à sa connexion WABA. L'audit n'a donc pas trouvé
la preuve d'une boutique SaaS indépendante et illimitée par entreprise avec
entitlements et commandes isolés par fiche.

### Paiements et abonnements

`payments.Transaction` connaît les méthodes MTN MoMo, Airtel Money, Orange Money,
carte, virement et coupon. `edu_platform` contient aussi une transaction dédiée et
un client `MobileMoneyService` avec du code d'initiation et des webhooks Orange
Money/MTN MoMo. Cependant :

- l'initiation du paiement de commande et des packs Premium redirige vers WhatsApp
  pour recevoir les instructions et confirmer l'accès ;
- la demande du plan Business crée une `PaymentRequest`, passe l'activation à
  « en attente », puis redirige vers WhatsApp pour validation ;
- le checkout EduCam Pro crée aussi une transaction puis redirige vers WhatsApp ;
  les méthodes d'initiation Orange/MTN du service ne sont pas appelées par ses vues
  d'abonnement dans le code inspecté ;
- l'existence d'un service API, d'un webhook ou d'une méthode de paiement n'est
  pas la preuve que le parcours d'abonnement Business E-Shelle utilise ce flux ;
- le code ne prouve pas une page de checkout SaaS en libre-service avec confirmation
  automatique de l'abonnement.

Il est possible de proposer le paiement Mobile Money avec validation manuelle,
mais l'offre doit clairement annoncer cette étape tant que le parcours opérateur
n'est pas intégré et vérifié.

## Inventaire des applications produit

`INSTALLED_APPS` regroupe plusieurs dizaines d'applications indépendantes. Les
fonctionnalités ci-dessous sont les surfaces concrètes relevées dans les modèles
et vues pertinents ; elles ne signifient pas qu'elles sont toutes reliées à un
seul abonnement.

| Domaine / applications | Fonctions concrètes présentes |
|---|---|
| Comptes et accès — `accounts`, `billing`, `payments`, `dashboard`, `api`, `chat` | profils/utilisateurs, plans et abonnements applicatifs, historique/paiement, coupons, code d'accès, reçus, notifications, paramètres, API de recherche et chat. |
| Activités et commerce — `business`, `boutique`, `services`, `artisans`, `shelle_premium` | fiches Business et vitrines, catalogues et avis, demandes de devis/services, profils et réalisations d'artisans, panier/commandes/téléchargements numériques, cartes de prestataires. |
| WhatsApp et marketing — `whatsapp_commerce`, `whatsapp_agent`, `adgen`, `facebook_agent`, `commercial_agent`, `phone_ocr_agent`, `seo_agent`, `audio_studio`, `ai_engine`, `e_shelle_ai` | voir les distinctions WhatsApp ci-dessus ; génération de contenu publicitaire, génération vocale/musicale, chat/image/vidéo IA avec quotas, prospects staff, extraction de numéros par OCR, publication Facebook, pages/SEO et données d'usage. Plusieurs parcours sont payants, réservés staff, dépendants d'API externes ou désactivés ; ils ne forment pas un même pack existant. |
| Immobilier et véhicules — `immobilier_cameroun`, `auto_cameroun`, `auto_ecole` | fiches de biens et véhicules, photos, favoris, publication/modification/suppression, réservations ou demandes de visite/essai, signalements, profils vendeurs/agents ; écoles et cours de conduite. |
| Petites annonces — `annonces_cam` | catégories, vendeurs, annonces/photos, boosts, favoris, conversations/messages, alertes, avis, signalements et remontées ; les vues couvrent la gestion d'annonce et la messagerie d'annonce. |
| Agriculture — `agro` | acteurs/producteurs, produits/photos/modération, offres commerciales et appels d'offres, demandes de devis et commandes, certifications, avis, prix de marché, questions IA et stock producteur ; catalogue, recherche, devis, commandes, dashboard et prix de marché. |
| Salons — `salonhub.salons`, `salonhub.bookings`, `salonhub.dashboard`, `salonhub.accounts` | salons, services, horaires d'ouverture, rendez-vous, créneaux disponibles, création de rendez-vous et gestion du salon, des services et du statut du rendez-vous. |
| Rencontre — `rencontres` | profils/photos, découverte, likes, matchs, blocages, conversations/messages, signalements, plans Premium, abonnement, coach et boosts. |
| Éducation — `edu_platform`, `formations`, `curriculum`, `content`, `progress`, `math_cm`, `EnglishPrepApp`, `GermanPrepApp`, `italian_courses`, `preparation_tests` | cours, chapitres/leçons, quiz/questions, inscriptions/progression/avis/certificats ; examens, sessions, réponses, compétences, analyse, coach IA, exercices, préparation aux tests et suivi. EduCam Pro ajoute plans, transactions Orange/MTN, codes d'accès, contrôle d'appareil et espace de cours protégé ; son parcours d'abonnement actuel redirige néanmoins vers WhatsApp au lieu d'appeler les méthodes d'initiation du service Mobile Money. |
| Mobilité — `germany_opportunities`, `lebenslauf`, `canada_resume`, `jobs` | offres Ausbildung/bourses, favoris, candidatures et simulations d'entretien ; profils CV Allemagne/Canada, expériences/formation/langues et génération de CV/documents ; offres emploi et candidatures. |
| Autres marchés — `resto`, `gaz`, `pharma`, `pressing`, `sante`, `transport_core`, `njangi`, `artist_hub`, `simplo`, `tchaslucpay`, `apps.tibo`, `lebelage_importer` | restaurants, menus/avis/favoris/analytics ; dépôts et avis de gaz ; médicaments, pharmacies et stocks ; pressings/services/commandes ; professionnels/produits santé et rendez-vous ; trajets/demandes ; adhésions et tontine ; casting/candidats/tickets/réservations ; demandes de services et livraisons ; comptes/transactions de paiement ; parcours de dropshipping Canada ; import de produits vers Shopify. Ces produits ont leurs modèles et vues propres, sans abonnement bundle commun démontré. |
| Infra et applications Django — `cloudinary_storage`, `cloudinary`, `rest_framework`, `rest_framework.authtoken`, `django.contrib.sites`, `allauth` et fournisseurs sociaux, `django_celery_beat`, `django_celery_results` | stockage média, API/token, domaines, connexion sociale et ordonnanceur/résultats de tâches ; ce sont des briques de plateforme, pas des fonctionnalités qui justifient à elles seules un pack client. |

## Grille tarifaire recommandée

### Hypothèses de conversion et de coût

- Référence indicative de calcul : **1 USD ≈ 600 XAF**. Ce n'est pas un taux
  contractuel ou une cotation en temps réel ; afficher le prix en XAF comme prix
  officiel et le dollar uniquement comme repère.
- Le VPS fourni coûte environ 12 USD/mois, soit environ **7 200 XAF/mois** avec
  cette conversion.
- Coût serveur fixe réparti illustrativement sur 10 clients payants :
  **7 200 / 10 = 720 XAF/client/mois**. Formule à recalculer avec le nombre de
  clients actifs : coût fixe par client = 7 200 / N.
- Les bénéfices ci-dessous soustraient uniquement cette part du VPS. Ils ne sont
  pas une marge nette comptable : ils excluent personnel/support, taxes, paiement,
  stockage/médias, sauvegardes, observabilité, APIs IA et frais Meta variables.
- Les prix des concurrents mentionnés par le propriétaire sont des références
  non vérifiées ici et les unités ne sont pas comparables : une API à l'envoi, un
  outil marketing et une licence CRM ne couvrent pas les mêmes coûts.

### Tableau récapitulatif

| Pack proposé | Prix / mois | Repère USD | Maturité commerciale actuelle |
|---|---:|---:|---|
| **Présence — Démarrage** | **5 000 XAF** | ≈ $8,33 | Proche du plan Pro déjà seedé ; paiement à valider manuellement. |
| **Croissance — Business** | **15 000 XAF** | ≈ $25,00 | Prix mis à jour dans le seed local ; appliquer la commande sur le VPS pour mettre à jour ProviderPlan. |
| **Premium — Croissance étendue** | **25 000 XAF** | ≈ $41,67 | Tarif existant dans le seed ; limite catalogue sans plafond déclaré. |
| **Empire — Multi-activité** | **35 000 XAF — sur devis** | ≈ $58,33 | Prix repère, mais activation manuelle ; aucun entitlement multi-apps unifié. |
| **Écosystème — Accompagnement** | **60 000 XAF — sur devis** | ≈ $100,00 | Prix repère, périmètre à confirmer manuellement ; pas de bundle prêt au checkout. |

### Comparatif fonctionnalités, limites et marge indicative

| Pack | Fonctions réellement disponibles à rattacher | Produits/services | Messages / contacts / sièges | WABA | Part VPS / reste avant coûts exclus |
|---|---|---:|---|---:|---:|
| Présence — Démarrage | Fiche Business, catalogue, CRM, réponses 24 h | 20 articles, 2 photos additionnelles/article | Pas de plafond mensuel de messages ou de contacts codé ; aucun siège équipe défini | 1 par fiche | 720 / 4 280 XAF ; 85,6 % |
| Croissance — Business | Démarrage + sync catalogue Meta + relances individuelles consenties (activation conditionnelle) | 50 articles, 4 photos additionnelles/article | Pas de plafond mensuel de messages ou de contacts codé ; aucun siège équipe défini ; worker max. 10 relances dues/minute | 1 par fiche | 720 / 14 280 XAF ; 95,2 % |
| Premium — Croissance étendue | Tout Croissance selon la description du seed ; visibilité premium, carrousels, accompagnement marketing | Pas de plafond déclaré, 7 photos additionnelles/article | Pas de plafond mensuel de messages ou de contacts codé ; aucun siège équipe défini ; worker max. 10 relances dues/minute | 1 par fiche | 720 / 24 280 XAF ; 97,1 % |
| Empire — Multi-activité | Modules indépendants (voir ci-dessous), activation manuelle à spécifier | Aucun quota commun de produits ou boutiques | Aucun quota de messages, contacts ou sièges défini pour un bundle | 1 par fiche si le WABA CRM est vendu | 720 / 34 280 XAF ; 97,9 % |
| Écosystème — Accompagnement | Périmètre de plusieurs modules à fixer au devis ; aucun bundle codé | Aucun quota commun défini | Aucun quota de messages, contacts ou sièges défini pour un bundle | 1 par fiche si le WABA CRM est vendu | 720 / 59 280 XAF ; 98,8 % |

La part VPS utilisée dans ce tableau suppose 10 abonnés payants et ne représente
pas le coût réel par entreprise : elle ne couvre que le partage du montant fixe
du VPS.

### Détail des packs

#### 1. Présence — Démarrage

**Cible :** petite entreprise qui veut une vitrine simple, un numéro WhatsApp
Business connecté et un fichier de contacts exploitable.

**À 5 000 XAF/mois (≈ $8,33)**, aligné sur le tarif Pro présent dans le seed :

- une fiche Business publique, ses coordonnées et lien de partage ;
- catalogue de la fiche jusqu'à **20 produits/services**, et jusqu'à **2 photos
  supplémentaires par article** ;
- une connexion WABA maximum par fiche (limite structurelle de la relation) ;
- CRM contacts avec étapes, tags, notes, consentement et prochaine relance ;
- réponses individuelles en texte dans la fenêtre WhatsApp de 24 heures ;
- 5 crédits IA par activation selon la logique du plan Pro.

**Limites honnêtes :** pas de synchronisation du catalogue vers Meta avec Pro ;
pas de relances par modèles avec Pro ; pas de sièges équipe ni quota mensuel
implémenté ; coûts Meta facturés séparément au client. Les plafonds de 20 articles
concernent le catalogue `BusinessCatalogItem`, pas une promesse de boutique
digitale isolée par client.

**Coût/marge illustrative :** coût VPS partagé 720 XAF/client, reste 4 280 XAF,
soit **85,6 %** avant tous les autres coûts (ce n'est pas une marge nette).

**Argument de vente :** profil local et CRM de base par entreprise, plutôt qu'une
API d'envoi seule comme le tarif Twilio communiqué par le propriétaire. Ne pas
promettre une connexion Meta opérationnelle tant que l'approbation et la
configuration ne sont pas vérifiées.

#### 2. Croissance — Business

**Cible :** PME qui reçoit des demandes sur WhatsApp et veut tenir un catalogue et
effectuer des relances autorisées.

**Prix recommandé : 15 000 XAF/mois (≈ $25)**. Le seed local a été mis à jour ;
la base de production ne sera alignée qu'après exécution de la commande seed sur
le VPS.

- fonctionnalités Présence ;
- jusqu'à **50 articles Business**, **4 photos supplémentaires par article** ;
- une connexion WABA maximum par fiche ;
- synchronisation de ces articles vers le catalogue Meta lié ;
- relances individuelles à date choisie avec modèle Meta approuvé et consentement
  explicite, retrait/STOP et suivi des statuts ;
- 20 crédits IA, 7 jours de boost inclus selon le seed ;
- pas de campagnes de masse dans `whatsapp_commerce`.

**Activation conditionnelle :** les relances exigent l'approbation du modèle,
consentement conforme, worker/Celery Beat opérationnel et
`WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True`. Le défaut du code est désactivé ;
ne pas vendre l'automatisation comme actuellement disponible en production avant
un test réel contrôlé. La connexion et la synchronisation nécessitent aussi les
permissions Meta et la configuration du serveur.

**Coût/marge illustrative :** coût VPS partagé 720 XAF/client, reste 14 280 XAF,
soit **95,2 %** avant les autres coûts.

**Argument de vente :** catalogue synchronisé et relances ciblées opt-in, à la
différence d'un outil générique de diffusion. Le prix WhatChimp de 35 USD cité
par le propriétaire n'a pas été vérifié et n'est pas comparable sans comparer
ses quotas, son usage Meta et ses fonctionnalités.

#### 3. Premium — Croissance étendue

**Cible :** entreprise qui veut le plafond catalogue déclaré le plus élevé et les
avantages Premium existants.
**Prix : 25 000 XAF/mois (≈ $41,67)**, déjà présent dans le seed.

- tout Croissance selon les droits Business/Premium et la description du seed ;
- pas de plafond d'articles déclaré pour `BusinessCatalogItem` ;
- jusqu'à **7 photos supplémentaires par article** ;
- 50 crédits IA et 15 jours de boost inclus selon le seed ;
- visibilité Top résultats IA, carrousels premium et accompagnement marketing,
  tels que décrits dans le seed (le périmètre exact doit être vérifié côté service).

**Limites honnêtes :** « sans plafond déclaré » ne promet pas un volume illimité
de stockage ou de synchronisation Meta ; aucun quota mensuel de messages,
contacts ou sièges n'est défini. L'automatisation reste conditionnée aux
prérequis Meta et au flag serveur.

**Coût VPS partagé :** 720 XAF/client pour 10 clients ; reste 24 280 XAF, soit
**97,1 %** avant les coûts exclus.

**Argument vs Twilio :** regrouper fiche, catalogue Business, CRM et outils de
présence au lieu d'une facturation API au message. La référence Twilio de
0,005 USD/message fournie par le propriétaire n'est pas vérifiée ici et ne
comprend pas nécessairement les mêmes composants.

#### 4. Empire — Multi-activité

**Cible :** entrepreneur qui gère plusieurs verticales E-Shelle.
**Prix indicatif : 35 000 XAF/mois (≈ $58,33), sur devis et activation manuelle.**

Les surfaces existantes à proposer **seulement après activation manuelle et
vérification des droits** sont :

- Immobilier : fiches/photos de biens, favoris, demandes de visite, statut réservé
  et espace agent ;
- Auto : annonces/photos de véhicules, favoris, statut réservé, espace vendeur et
  demande d'essai ;
- Annonces Cam : catégories, vendeurs, annonces, favoris, conversations/messages
  et gestion par le vendeur ;
- Agro : profils d'acteurs, produits, offres/appels d'offres, demandes de devis,
  commandes et prix de marché ;
- Éducation : formations/leçons/progression et parcours d'examens des modules
  d'apprentissage.

Leurs vues et données ne sont pas une idée ou un simple document. En revanche, le
dépôt n'établit pas un achat unique qui active toutes ces applications au même
utilisateur. Les plans Premium sont par application/module, et les routes
d'activation peuvent rediriger vers une validation WhatsApp.

**Ce qu'il est raisonnable de vendre aujourd'hui :** offre personnalisée avec
activation manuelle de modules nommés dans le devis, après contrôle des droits,
prix propres à ces modules et accès client. **Ne pas annoncer** « tout
l'écosystème », multi-boutique illimitée, équipe multi-utilisateurs ou
interconnexion automatique sous un seul forfait.

**Limites incluses :** non déterminées dans un entitlement Empire ; chaque module
conserve ses propres limites et règles. Le plafond WhatsApp reste une connexion
WABA par fiche ; aucun quota d'envoi ni quota de sièges d'équipe n'est défini.

**Coût/marge indicative uniquement :** si vendu avec la même hypothèse de 10
clients, 720 XAF de VPS partagé, reste théorique 34 280 XAF soit **97,9 %** avant
les coûts exclus. Cette marge ne tient pas compte du coût d'accompagnement et
des services externes d'un bundle multi-module.

**Argument de vente :** proposer plusieurs marchés depuis une marque locale,
mais seulement après avoir défini un périmètre écrit ; ne pas comparer ce bundle
à un tarif par message Twilio ou à un outil de campagne.

**Argument vs Twilio :** le prix sur devis rémunère un périmètre d'activation de
modules E-Shelle plutôt qu'un coût de transport par message ; il ne constitue pas
un substitut fonctionnel direct à une API de messagerie.

#### 5. Écosystème — Accompagnement

**Cible :** entreprise ou réseau qui souhaite plusieurs activités, configuration
et accompagnement.
**Prix indicatif : 60 000 XAF/mois (≈ $100)**, sur devis et avec liste des
applications activées.

Ce prix n'est pas encore un pack implémenté. Les surfaces déjà codées couvrent les
modules de l'inventaire (verticales marketplace, rencontre, agro, salons,
éducation/immigration et outils de contenu/IA) ; elles restent des applications
distinctes, avec leurs propres modèles et vues. Le vendre seulement comme contrat
manuel dont le périmètre, l'activation et les prestations sont confirmés avant
facturation. Le coût serveur illustratif reste 720 XAF/client dans l'hypothèse
de 10 comptes (reste 59 280 XAF, **98,8 %** avant coûts exclus) ; cette formule
ne valorise ni support, ni configuration, ni services IA, ni commissions.

**Prérequis avant vente self-service :** table de bundle et entitlements
multi-application, nombre de fiches et sièges, quotas, prix d'add-ons, paiement
MoMo/Orange vérifié, facture et gestion de renouvellement. À défaut, ce pack est
« sur devis », pas « tout illimité ».

**Argument vs Twilio :** proposer une mise en place coordonnée des applications
E-Shelle retenues, et non vendre un prix/message ou promettre des intégrations
multi-apps qui n'existent pas encore.

## Comparaison concurrentielle — précautions de communication

Les comparatifs ci-dessous reprennent uniquement les données données par le
propriétaire : Twilio à 0,005 USD/message (environ 3 XAF au taux indicatif),
UMVA à 5 USD et WhatChimp à 35 USD. Ces chiffres, périmètres, dates et frais
supplémentaires n'ont pas été vérifiés dans cet audit.

| Solution | Différence de modèle à mettre en avant | Précaution |
|---|---|---|
| Twilio | E-Shelle peut associer fiche locale, catalogue, contacts et workflows de CRM au WABA du client. | Twilio est notamment une API de communication ; ne pas comparer directement un tarif/message à un abonnement CRM. Les frais Meta peuvent s'ajouter dans les deux cas. |
| UMVA | Positionner E-Shelle sur l'onboarding officiel, l'identité de l'entreprise, le consentement et le support local vérifiables. | Ne pas publier « fake », « sans KYC » ou une accusation de blocage sans preuve vérifiable et actuelle. |
| WhatChimp | E-Shelle se différencie potentiellement par le catalogue et la fiche business locale liés au WABA client, avec relances consenties. | Ne pas prétendre que la concurrence est non conforme ou plus chère sans source datée et comparaison fonctionnelle identique. |

## URLs publiques existantes et App Review

URLs à fournir après contrôle qu'elles sont accessibles sans connexion et servent
les pages courantes :

- Contact : `https://e-shelle.com/services/contact/`
- Politique de confidentialité : `https://e-shelle.com/privacy-policy`
- Conditions : `https://e-shelle.com/terms`
- À propos : `https://e-shelle.com/about`
- Plans prestataires existants : `https://e-shelle.com/business/plans/`

Les quatre premières sont les pages de conformité/contact à prioriser pour les
informations publiques de l'application. La page Plans est fournie par les
`ProviderPlan` actifs en base ; vérifier ses contenus et prix de production avant
de la présenter comme grille officielle. Une page publique dédiée
`/services/whatsapp-business/` pourrait expliquer la connexion, les responsabilités
de facturation Meta et la désinscription, mais **elle n'a pas été trouvée comme
route existante** pendant l'audit : ne pas la soumettre avant création, test et
publication.

Les pages légales déclarent notamment les traitements WhatsApp et l'hébergement
communiqués par le propriétaire. Confirmer leur exactitude avec la configuration
et les pratiques réelles avant App Review. Le statut « premier Meta Tech Provider
d'Afrique Centrale » reste une déclaration non vérifiée par le code ; attendre la
décision Meta avant de l'afficher comme statut acquis.

## Décisions produit et travaux avant d'annoncer les prix

1. Choisir les offres réellement vendables : Pro à 5 000 XAF, Business à
   15 000 XAF (seed modifié localement, commande serveur encore nécessaire) et
   Premium à 25 000 XAF.
2. Définir explicitement l'unité de facturation : par fiche Business, par WABA,
   par numéro ou par utilisateur. Le code actuel est par fiche et limite à une
   connexion par fiche.
3. Ne pas promettre « produits illimités », « messages illimités », « utilisateurs
   illimités » ou « tous les modules » : aucun de ces forfaits complets n'est
   défini comme entitlement.
4. Vérifier App Review, Tech Provider, permissions, actifs Meta, modèles, webhook,
   worker et configuration VPS ; effectuer un test d'envoi opt-in et confirmer le
   statut de livraison avant activation.
5. Choisir paiement manuel clairement présenté ou intégrer et tester un checkout
   MTN MoMo/Orange Money avec webhooks authentifiés, rapprochement, reçus et
   renouvellement. Les choix de méthode présents dans un modèle ne suffisent pas.
6. Pour Empire et Écosystème, créer avant l'auto-service une matrice de droit
   multi-apps, une politique de sièges, quotas, parcours de facturation et
   reporting par module.
7. Mesurer les coûts sur plusieurs mois et au moins 10/50/100 entreprises avant
   de publier des marges nettes. Isoler dans la comptabilité les frais Meta,
   APIs IA, stockage, paiements, support et taxes.
