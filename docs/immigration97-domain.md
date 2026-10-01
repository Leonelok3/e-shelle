# Domaine Immigration97 : preparation et mise en service

Statut au 1 octobre 2026 09:30 UTC : DEPLOYE sur le VPS. DNS @ et www
pointent sur 162.35.112.26. Certificat Let's Encrypt dedie obtenu pour les deux
noms, expiration 2026-12-30. Configuration HTTPS active, nginx -t valide.
Renouvellement programme via certbot.timer ; hook dedie pour recharger Nginx.
Les tests HTTPS depuis le VPS passent : racine et www vers /canada/, preparation,
offres Canada, images/CSS/JS, formulaire login avec CSRF (donnees vides, aucun
compte cree), boutique renvoyee vers E-Shelle et pages E-Shelle inchangees.
La connexion HTTP externe depuis le poste de controle echoue egalement vers
E-Shelle : controle visuel par l'utilisateur encore necessaire. Aucun test
de paiement reel ni de connexion sociale effectue.
Sauvegarde avant activation : /root/immigration97-backup-20261001-092437.
Sauvegarde initiale : /root/immigration97-backup-20261001-092331.
Sept tests passent sur le VPS, Django check et nginx -t passent.
Test direct Gunicorn avec Host immigration97.com : /canada/ 200,
/boutique/ redirige vers https://e-shelle.com/boutique/.
Apres rechargement, accueil, Canada, boutique et formations E-Shelle : HTTP 200.
Le contenu .env est restaure a sa valeur initiale ; son proprietaire est
eshelle:www-data, mode 600, pour permettre la lecture par Django.

## Comportement prepare

- immigration97.com/ ouvre /canada/ sur le meme domaine.
- /canada/, /prep/ et /jobs/canada/ restent sur Immigration97.
- Comptes, facturation, paiements, ressources et pages legales restent accessibles.
- Les autres applications renvoient vers le meme chemin sur e-shelle.com.
  Les POST hors perimetre sont refuses plutot que de transferer leur contenu.
- Les requetes e-shelle.com restent inchangees. Aucune migration de donnees.
- Les comptes sont communs, mais les sessions sont propres a chaque domaine.
- Le sitemap global E-Shelle n'est pas publie sur le nouveau domaine.
- L'ancienne URL e-shelle.com/canada/ continue de fonctionner pendant la validation.

## Ordre de deploiement

1. Retablir SSH avec une cle autorisee (ne pas partager de cle privee).
2. Lire la configuration ACTIVE avec nginx -T, les services et les chemins.
   Verifier le socket Gunicorn, static/media, les versions du code, les cookies,
   les limites de requetes et les en-tetes TLS. Le fichier Nginx fourni est un
   modele base sur le depot, pas une copie validee du VPS.
3. Sauvegarder les fichiers qui seront modifies, le .env et la configuration
   Nginx active, avec leurs permissions ; exporter les DNS Hostinger.
   Garder les sauvegardes .env hors du depot et non accessibles par le Web.
4. Deployer seulement edu_cm/immigration_domain.py et la ligne de middleware
   dans edu_cm/settings.py, avant SessionMiddleware et CsrfViewMiddleware.
   Ajouter les domaines et origines HTTPS aux listes ALLOWED_HOSTS et
   CSRF_TRUSTED_ORIGINS dans settings.py comme dans le depot.
   Ne pas remplacer les domaines E-Shelle existants ni modifier le .env.
5. Executer manage.py check et les tests de routage, puis recharger le service
   applicatif avec le mecanisme deja utilise sur le VPS.
6. Preparer un site Nginx SEPARE immigration97, seulement son bloc HTTP au depart.
   Ne pas activer les blocs HTTPS avant que les certificats existent.
   Verifier nginx -t puis recharger Nginx. Verifier E-Shelle immediatement.
7. Dans Hostinger, apres verification de l'IP VPS, remplacer le A @ par
   162.35.112.26 et creer/adapter www CNAME immigration97.com.
   Verifier les A/AAAA de @ et www : aucun ne doit pointer sur l'ancien serveur.
   Conserver MX, SPF, DKIM, DMARC et les autres sous-domaines/services.
8. Une fois le DNS confirme, creer un certificat dedie, sans modifier celui
   d'E-Shelle :

   certbot certonly --webroot -w /var/www/letsencrypt -d immigration97.com -d www.immigration97.com

9. Activer les blocs HTTPS du modele, apres adaptation aux chemins verifies.
   nginx -t doit reussir AVANT systemctl reload nginx.
10. Tester HTTPS, accueil, assets, compte existant, inscription, deconnexion,
    CSRF sur formulaire, parcours, TCF/TEF, CV, offres et retour de paiement.
    Pour Google/Facebook, verifier les URI de retour chez les fournisseurs avant
    d'annoncer ces modes de connexion disponibles sur le nouveau domaine.
    Verifier aussi accueil E-Shelle et plusieurs autres applications.
11. Apres validation, convertir la normalisation www/HTTP en redirections 301.
    Inventorier les anciennes URL immigration97.com avant de definir leurs
    redirections SEO ; ne pas rediriger aveuglement toutes les anciennes pages.
    Preparer un sitemap Canada dedie et la canonicalisation de l'ancien /canada/
    apres verification de la navigation et des sessions existantes.

## Retour arriere

Restaurer les DNS exportes et les seuls fichiers modifies a partir des sauvegardes.
Desactiver seulement le nouveau site Nginx, verifier nginx -t, puis recharger.
Restaurer/recharger le code applicatif si necessaire. Aucun changement de base
de donnees n'est requis. La propagation DNS peut retarder le retour des visiteurs.

## Tests locaux

    .\.venv\Scripts\python.exe manage.py test edu_cm.test_immigration_domain --settings=preparation_tests.test_settings

Les tests couvrent l'isolation des domaines, les chemins Canada, les cookies,
les redirections, les POST et le sitemap. Ils ne remplacent pas les tests reels
Nginx/TLS, de connexion ou de paiement sur le VPS.
