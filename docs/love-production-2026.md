# E-Shelle Love : audit et mise à niveau

## Positionnement et offres

Rencontres locales et internationales entre adultes en Afrique, en Europe et au Canada. Le gratuit doit permettre une vraie conversation après un match. Les pass achètent davantage de découverte, de visibilité et de contrôle ; ils ne garantissent pas une relation et ne contournent jamais un refus ou un blocage.

| Offre | Prix de lancement existant conservé | Inclus |
|---|---:|---|
| Découverte | 0 FCFA | 15 likes/jour, 1 super like/jour, messages sans quota quotidien avec les matchs, 6 photos, filtres de base, conseils, blocage et signalement |
| Pass 3 jours | 1 200 FCFA | Likes sans quota, 3 super likes/jour, voir les likes reçus, 8 photos |
| Pass 10 jours | 2 500 FCFA | Likes sans quota, 10 super likes/jour, 12 photos, retour au dernier profil passé, 1 boost/7 jours, filtre d’études, mode discret |
| Pass 30 jours | 4 900 FCFA | Avantages du pass 10 jours, super likes sans quota, 3 boosts/7 jours, statistiques |

Les valeurs payantes viennent des plans existants en base (migration 0003), restent administrables et ne sont pas écrasées par cette mise à niveau. Les quotas gratuits sont dans `RENCONTRES_SETTINGS`. Les boosts durent 30 minutes, avec quota sur 7 jours glissants. Tous les envois restent soumis aux protections anti-spam. Il n’y a pas de prélèvement automatique.

Ces tarifs sont une hypothèse commerciale de lancement, pas une étude de disposition à payer valable pour toute l’Afrique. Mesurer par ville et pays : profils avec photo publiée, premiers matchs, première réponse, rétention à 7/30 jours, conversion par pass, remboursements et signalements. Éviter d’acheter du trafic tant que les utilisateurs d’une même zone ne trouvent pas suffisamment de profils réels et actifs. Ne pas semer de faux profils en production.

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

Après déploiement, avec deux comptes de test majeurs : uploader une photo et vérifier sa publication immédiate, choisir la photo principale, faire un match réciproque, échanger deux messages, bloquer et confirmer que l’autre compte ne peut plus écrire. Créer une demande de pass, vérifier le paiement dans le compte marchand, puis utiliser l’action d’activation des abonnements dans l’administration Rencontres. Ne pas simplement modifier le statut de la transaction dans l’administration générale Paiements.

Si le contrôle échoue : conserver la sortie, consulter `sudo journalctl -u eshelle -n 80 --no-pager`. La migration 0006 ajoute des champs ; un retour au code précédent peut conserver ces colonnes. Ne pas restaurer automatiquement une sauvegarde qui écraserait les nouveaux messages ou paiements reçus depuis.

## Validation et limites

Les tests automatisés utilisent des bases de test indépendantes et de vrais schémas/migrations : expiration, quotas, découverte, incognito, blocage, chat, paiement répété, renouvellement, boost, photos, majorité, permissions et rendu des pages. Commande rapide :

```bash
python manage.py test rencontres.test_production --settings=rencontres.test_settings --noinput
```

Une première passe de 13 tests a aussi réussi avec la configuration complète du projet. Les captures `output/love/premium-desktop.png` et `premium-mobile.png` sont des rendus locaux avec données de démonstration des tarifs, pas des captures de production. Les contrôles JavaScript simulent les réponses réseau ; ils ne remplacent pas le contrôle avec deux comptes sur le VPS.

Points d’exploitation restant nécessaires : équipe disponible pour traiter les signalements et vérifier les paiements, critères documentés de vérification d’identité, surveillance des signalements, mesure des performances PostgreSQL et charge réelle. Les comptes marqués vérifiés avant cette correction doivent être revus : le code historique pouvait attribuer ce badge à l’approbation d’une photo.

Les médias historiques restent servis selon la configuration existante ; cette version ne transforme pas les anciennes URL de médias en URL privées à durée limitée et ne supprime pas rétroactivement les fichiers originaux. Le mode discret masque la découverte, il ne révoque pas une URL de photo déjà partagée. Avant de promettre des photos privées ou éphémères, prévoir un stockage privé et des autorisations de téléchargement. Les paiements automatisés, KYC par prestataire, appels vidéo et notifications push ne sont pas présentés comme disponibles.


## Publication immédiate des photos — 3 octobre 2026

La création d’un profil redirige vers l’ajout des photos. Les nouveaux uploads sont publiés immédiatement, sans validation administrative préalable. Les contrôles de format, dimensions, poids et réencodage restent actifs. Les préférences de découverte, le mode discret, les blocages et la désactivation restent respectés ; publier une photo ne confère aucun badge d’identité.

La migration 0007 publie aussi les photos déjà en attente, synchronise la photo principale et recalcule la complétion des profils concernés. Les photos précédemment rejetées et supprimées ne sont pas restaurées. La migration ne remet pas les photos en attente en cas de retour arrière. Exécuter le script de déploiement ci-dessus pour appliquer ce changement en production.


## Ambiance et parcours visuels — 3 octobre 2026

Nouvel accueil public et connecté, palette prune et rose, cartes de découverte agrandies, accès directs au profil et au coach, états vides plus utiles. Titres et invitations actualisés sur Découvrir, Matchs, Messages, Photos et l’édition du profil. La feuille love-experience.css est commune aux pages Love, y compris les offres et paramètres.

Animations légères à l’apparition des sections, interactions au survol et éclats lors d’un vrai match. Le réglage prefers-reduced-motion est respecté. Les cartes et liens restent visibles sans JavaScript ; aucune animation ne retarde une action. Le déploiement doit inclure collectstatic pour les deux nouveaux fichiers CSS et JavaScript.

Validation : 19 tests de parcours réussis, contrôle syntaxique JavaScript, huit pages rendues avec une base de test isolée dans output/love-preview. Aucun navigateur connecté dans la session : la vérification visuelle desktop/mobile reste à effectuer avant publication.


## Positionnement local et international — 3 octobre 2026

Signature : « Tout près. Au-delà des frontières. À votre rythme. » L’accueil public, l’espace membre, la découverte, les offres et le Coach Love présentent désormais explicitement l’Afrique, l’Europe et le Canada. Le service reste actuellement en français : ces changements ne constituent pas une traduction multilingue.

Les cinq horizons (Sans frontières, Ma ville, Afrique, Europe, Canada) sont opérationnels en session. Un changement d’horizon par POST protégé par CSRF retire les anciens pays, ville et distance, tout en conservant l’âge, la religion et la langue. Ma ville compare la ville déclarée et le pays de résidence ; ce n’est pas un rayon GPS. Les filtres gratuits permettent aussi de préciser la ville et une langue. Un pays incompatible avec le continent sélectionné produit une erreur explicite.

Pour la diaspora, le pays de résidence renseigné remplace le pays principal dans les recherches et les cartes. S’il est vide, le pays principal reste utilisé. La nationalité n’est jamais utilisée comme lieu de résidence. Les règles de majorité, préférences réciproques, blocage, mode discret et compte actif continuent de s’appliquer. Le Coach propose des amorces adaptées à deux pays différents et aux langues réellement déclarées.

### Pages publiques et SEO/GEO

Pages : accueil Love, gratuit/pass, sécurité, rencontres internationales, Afrique, Europe, Canada, Cameroun, Douala et Yaoundé. Les destinations ont un contenu distinct, des liens internes et un fil d’Ariane. Les questions fréquentes sont visibles en HTML et partagent la même source que le JSON-LD. Les balises WebSite, WebPage, BreadcrumbList et FAQPage décrivent le contenu réel. Aucun avis, score client, effectif par ville ni classement mondial n’est inventé. Le balisage FAQ ne promet pas un résultat enrichi Google.

Ajout de canonical, Open Graph et Twitter Card avec un visuel local 1200 × 630. RENCONTRES_PUBLIC_ORIGIN, par défaut SITE_URL (https://e-shelle.com), fournit l’origine canonique et doit être cohérent avec le domaine de production. Les pages Love publiques sont ajoutées au sitemap principal ; leur lastmod correspond à la modification éditoriale du 3 octobre 2026. Les profils et messages ne sont pas ajoutés au sitemap. Les espaces membres restent noindex ; robots.txt exclut également les chemins des profils, messages et actions privées. robots.txt ne remplace pas l’authentification.

Le GEO suit les bases indiquées par Google Search Central : contenu textuel utile, liens accessibles et données structurées conformes au contenu visible. Pas de fichier prétendument magique pour garantir une citation par les IA.

Sources officielles consultées :
- https://developers.google.com/search/docs/appearance/ai-features
- https://www.bing.com/webmasters/help/bing-webmaster-guidelines-30fba23a
- https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c

### Validation et mise en ligne

30 tests automatisés réussis : résidence diaspora, cinq horizons, filtre de langue, cohérence HTML/AJAX, changements par POST, conflits de filtres, pages publiques, canonical sans paramètres de suivi, JSON-LD analysable et échappé, FAQ visible, sitemap, robots et Coach international. Les tests antérieurs de photos, matchs, messages, paiements et blocages restent verts. Le contrôle Django complet et le contrôle des migrations sont réussis. Seize pages de prévisualisation sont rendues avec une base de test indépendante dans output/love-preview. Le navigateur de contrôle n’est pas connecté : la validation visuelle sur téléphone et ordinateur reste nécessaire avant publication.

La migration photo 0007 du travail précédent et collectstatic restent requis. Le contrôle check_love_production inclut les nouveaux CSS, JavaScript et le visuel de partage. Pour ces changements, le script cible deploy/update_love.sh reste applicable ; le code n’a pas été publié depuis cette session. Après déploiement, vérifier /robots.txt, /sitemap.xml et les URL canoniques. Soumettre le sitemap et inspecter les nouvelles pages dans Google Search Console et Bing Webmaster Tools depuis les comptes du propriétaire. Suivre ensuite impressions, clics, citations IA disponibles et inscriptions ; aucune soumission ni mesure externe n’a été effectuée ici.
