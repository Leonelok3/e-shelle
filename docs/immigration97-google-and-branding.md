# Immigration97 : Google et identite publique

## Deploiement du 1 octobre 2026

Sauvegarde identite : /root/immigration97-identity-20261001-095605.
Les titres, textes et pieds de page Canada/preparation/opportunites utilisent
Immigration97 sur le domaine dedie. L'espace compte et la page des offres sont
limites au module prep sur ce domaine. Les valeurs par defaut restent E-Shelle
sur les autres domaines. Les liens WhatsApp generes pour les offres utilisent
la marque du domaine, sans envoi automatique de message.

Verification : 82 templates compiles, tests de domaines/OAuth, Django check.
Pages publiques Canada, prep, offres Canada, login, inscription, billing et
acces : HTTP 200 et aucune mention E-Shelle dans le texte visible analyse.
Accueil, boutique, formations et login E-Shelle : HTTP 200.

## Erreur Google confirmee

Le fournisseur Google refuse l'URI non autorisee. L'application transmet :

    https://immigration97.com/accounts/social/google/login/callback/

Client actuellement utilise :

    883675735614-d4qnr25l626t2571drpm0vubj4l0im6q.apps.googleusercontent.com

Dans Google Cloud / Google Auth Platform / Clients, ajouter exactement cette
URI au client existant, en conservant toutes les URI E-Shelle. La correction
est a effectuer dans Google Cloud ; elle ne peut pas etre remplacee par une
modification DNS ou Nginx. Ne pas faire passer la connexion par e-shelle.com.

## Identite Google completement distincte

Le nom de l'ecran de consentement depend du projet Google, pas du domaine
de la requete. Pour une identite Immigration97 independante, creer un projet
Google Auth Platform dedie, avec marque Immigration97, domaine autorise
immigration97.com, accueil et liens de confidentialite/conditions exacts.
Configurer l'audience et la publication selon les exigences Google ; un projet
en mode test ne permet pas la connexion de tous les visiteurs.

Creer un client OAuth Web avec l'URI ci-dessus. Placer ses identifiants dans
le .env du VPS (ne pas transmettre de secret dans le chat) :

    IMMIGRATION97_GOOGLE_CLIENT_ID=...
    IMMIGRATION97_GOOGLE_CLIENT_SECRET=...

Le SocialAccountAdapter selectionne ces identifiants uniquement sur
Immigration97 ; les identifiants E-Shelle restent inchanges. Le service systemd
charge aussi le .env : verifier les valeurs effectives et recharger/redemarrer
de facon controlee apres configuration.

## Reste a valider

- Enregistrement Google Cloud puis connexion Google reelle avec retour au parcours.
- Marque Google dediee si le projet partage affiche encore E-Shelle.
- Parcours authentifie complet et paiements reels : non executes durant cet audit.
- Identite expediteur des emails, documents generes et configuration des
  prestataires de paiement : audit supplementaire avant de promettre une
  independance de marque integrale. Les informations legales existantes ne
  doivent pas etre remplacees par une identite juridique inventee.
- Aucun navigateur connecte disponible pour modifier Google Cloud dans cette session.
