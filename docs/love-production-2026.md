# E-Shelle Love : audit et mise à niveau

## Positionnement et offres

Rencontres entre adultes au Cameroun et dans la diaspora. Le gratuit doit permettre une vraie conversation après un match. Les pass achètent davantage de découverte, de visibilité et de contrôle ; ils ne garantissent pas une relation et ne contournent jamais un refus ou un blocage.

| Offre | Prix de lancement existant conservé | Inclus |
|---|---:|---|
| Découverte | 0 FCFA | 15 likes/jour, 1 super like/jour, messages sans quota quotidien avec les matchs, 6 photos, filtres de base, conseils, blocage et signalement |
| Pass 3 jours | 1 200 FCFA | Likes sans quota, 3 super likes/jour, voir les likes reçus, 8 photos |
| Pass 10 jours | 2 500 FCFA | Likes sans quota, 10 super likes/jour, 12 photos, retour au dernier profil passé, 1 boost/7 jours, filtre d’études, mode discret |
| Pass 30 jours | 4 900 FCFA | Avantages du pass 10 jours, super likes sans quota, 3 boosts/7 jours, statistiques |

Les valeurs payantes viennent des plans existants en base (migration 0003), restent administrables et ne sont pas écrasées par cette mise à niveau. Les quotas gratuits sont dans `RENCONTRES_SETTINGS`. Les boosts durent 30 minutes, avec quota sur 7 jours glissants. Tous les envois restent soumis aux protections anti-spam. Il n’y a pas de prélèvement automatique.

Ces tarifs sont une hypothèse commerciale de lancement, pas une étude de disposition à payer valable pour toute l’Afrique. Mesurer par ville et pays : profils avec photo approuvée, premiers matchs, première réponse, rétention à 7/30 jours, conversion par pass, remboursements et signalements. Éviter d’acheter du trafic tant que les utilisateurs d’une même zone ne trouvent pas suffisamment de profils réels et actifs. Ne pas semer de faux profils en production.

L’attention au poids des images et au coût d’entrée répond aux obstacles d’accessibilité décrits par la [GSMA, Mobile Economy Africa 2026](https://www.gsma.com/solutions-and-impact/connectivity-for-good/mobile-economy/africa/). Le [paiement marchand Orange Money au Cameroun](https://orangemoneybusiness.orange.cm/services/paiement-marchand) existe, mais cela ne signifie pas que cette application dispose d’un contrat marchand ou d’une intégration API activée. Cette version conserve un parcours manuel honnête : demande enregistrée, coordonnées confirmées par l’équipe, paiement vérifié, activation administrative.

## Corrections livrées

- Réception des messages via un endpoint dédié, curseur initial à zéro, dédoublonnage à l’affichage et conservation du brouillon en cas d’échec réseau. Le polling s’arrête lorsque l’onglet est caché ou le navigateur hors ligne.
- Contrôle de l’appartenance à la conversation, des matchs désactivés, des blocages et des comptes suspendus avant lecture/envoi. Le marquage lu exige un POST.
- Droits calculés depuis un abonnement réellement actif et non depuis un booléen périmé. Quotas spécifiques à chaque plan.
- Demande de paiement validée côté serveur et créée avec l’abonnement dans une transaction. Une nouvelle soumission pour le même pass retrouve la demande en attente. Pas de prix fourni par le navigateur.
- Activation administrative réexécutable sans ajout répété de jours. Le renouvellement du même pass conserve les jours restants. Un changement de formule attend l’expiration du pass actif.
- Filtres utilisés dans la découverte initiale et AJAX ; respect du masquage de distance et du mode discret ; âge adulte et préférences mutuelles. Les distances inconnues ne sont plus présentées comme 9 999 km.
- Boost persistant, quota contrôlé et classement effectif parmi les profils compatibles. Retour au dernier profil passé opérationnel.
- Cartes de découverte : le profil affiché correspond au profil liké ; champs utilisateur échappés et JSON protégé contre l’injection HTML ; pas de passage silencieux au profil suivant après échec réseau.
- Photos : compteur incluant les photos en attente, erreurs affichées, minimum 300 × 300, maximum 5 Mo / 25 mégapixels, normalisation WebP et dimensions réduites à 1 600 px. Réencodage sans métadonnées EXIF. Sélection et suppression de la photo principale synchronisées.
- L’approbation d’une photo ne crée plus un badge d’identité vérifiée. La modération exige la permission correspondante.
- Accueil et comparaison des offres accessibles avant inscription ; navigation ordinateur, page de sécurité et mise en page mobile des offres.

## Déploiement depuis le VPS

Le poste de développement ne dispose pas d’un accès SSH accepté. Le déploiement doit donc être exécuté depuis la session VPS du propriétaire.

```bash
cd /home/eshelle/app
sudo -u eshelle git pull --ff-only origin main
sudo bash deploy/update_love.sh
```

Le script effectue le contrôle Django, une sauvegarde de la base sous `/home/eshelle/love-backups/` (hors répertoire web), la migration ciblée rencontres, `collectstatic`, le redémarrage d’E-Shelle et le contrôle des URL statiques avec leurs empreintes réelles. Pour PostgreSQL, `pg_dump` doit être installé et compatible avec le serveur. Si la sauvegarde échoue, la migration n’est pas exécutée. Aucune nouvelle dépendance d’exécution n’est nécessaire.

Ne pas lancer `seed_love_demo` en production. Le script ne déploie pas les autres services E-Shelle.

Après déploiement, avec deux comptes de test majeurs : uploader puis approuver une photo, choisir la photo principale, faire un match réciproque, échanger deux messages, bloquer et confirmer que l’autre compte ne peut plus écrire. Créer une demande de pass, vérifier le paiement dans le compte marchand, puis utiliser l’action d’activation des abonnements dans l’administration Rencontres. Ne pas simplement modifier le statut de la transaction dans l’administration générale Paiements.

Si le contrôle échoue : conserver la sortie, consulter `sudo journalctl -u eshelle -n 80 --no-pager`. La migration 0006 ajoute des champs ; un retour au code précédent peut conserver ces colonnes. Ne pas restaurer automatiquement une sauvegarde qui écraserait les nouveaux messages ou paiements reçus depuis.

## Validation et limites

Les tests automatisés utilisent des bases de test indépendantes et de vrais schémas/migrations : expiration, quotas, découverte, incognito, blocage, chat, paiement répété, renouvellement, boost, photos, majorité, permissions et rendu des pages. Commande rapide :

```bash
python manage.py test rencontres.test_production --settings=rencontres.test_settings --noinput
```

Une première passe de 13 tests a aussi réussi avec la configuration complète du projet. Les captures `output/love/premium-desktop.png` et `premium-mobile.png` sont des rendus locaux avec données de démonstration des tarifs, pas des captures de production. Les contrôles JavaScript simulent les réponses réseau ; ils ne remplacent pas le contrôle avec deux comptes sur le VPS.

Points d’exploitation restant nécessaires : équipe disponible pour examiner les photos et les paiements, critères documentés de vérification d’identité, surveillance des signalements, mesure des performances PostgreSQL et charge réelle. Les comptes marqués vérifiés avant cette correction doivent être revus : le code historique pouvait attribuer ce badge à l’approbation d’une photo.

Les médias historiques restent servis selon la configuration existante ; cette version ne transforme pas les anciennes URL de médias en URL privées à durée limitée et ne supprime pas rétroactivement les fichiers originaux. Le mode discret masque la découverte, il ne révoque pas une URL de photo déjà partagée. Avant de promettre des photos privées ou éphémères, prévoir un stockage privé et des autorisations de téléchargement. Les paiements automatisés, KYC par prestataire, appels vidéo et notifications push ne sont pas présentés comme disponibles.
