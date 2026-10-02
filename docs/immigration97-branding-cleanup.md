# Immigration97 : identité et contact

Contact public de paiement et assistance : **+237 693 649 944**.
Les liens WhatsApp utilisent `237693649944` et la marque Immigration97.
Aucun message n'est envoyé automatiquement.

Le domaine Immigration97 et les anciens accès Canada/préparation, dont
`/accounts/upgrade/?app=prep` sur le portail partagé, affichent Immigration97.
Les cookies du portail partagé sont conservés sur les anciens accès ; les
cookies Immigration97 restent limités à leur hôte. Les pages étrangères au
parcours sur immigration97.com répondent 404 plutôt que de renvoyer vers une
autre marque. Les autres modules sur le portail partagé gardent leur identité.

Les textes des plans et des anciens contenus affichés sont adaptés à la
marque au rendu : aucune modification des prix, droits premium, codes,
abonnements ou historiques stockés. Les prochains conseils IA utilisent
Immigration97. Les reçus et corps des emails sont également adaptés.

L'identité du compte WhatsApp Business (nom et photo) se règle dans le compte
WhatsApp du numéro indiqué. La marque de consentement Google se règle dans
le projet Google dédié : voir immigration97-google-and-branding.md.
Ces réglages externes ne sont pas remplacés par une modification du code.

Pour un expéditeur email entièrement indépendant, configurer dans le .env du
VPS `IMMIGRATION97_DEFAULT_FROM_EMAIL` avec une adresse Immigration97 réellement
autorisée par le fournisseur SMTP. Sans cette configuration, le nom affiché
est Immigration97 mais l'adresse technique de l'expéditeur existant est
conservée pour maintenir la livraison. Le script affiche seulement si cette
configuration et le client Google dédié sont présents, sans leurs valeurs.

Déploiement après commit/push, dans la session SSH root :

```bash
cd /home/eshelle/app &&
sudo -u eshelle git pull --ff-only origin main &&
bash deploy/update_immigration97_branding.sh
```

Ce script sauvegarde la base, exécute Django check, redémarre le service et
vérifie les pages publiques, leur marque, leurs liens et les assets. Pas de
migration ni d'appel à un prestataire de paiement. Les tests isolés vérifient
également le rendu authentifié de la page premium, le numéro WhatsApp, les
emails et la conservation des données des offres.
