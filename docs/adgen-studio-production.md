# Mise en production AdGen Studio

Cette version réunit campagnes, bibliothèque audio, sélection de médias et montage photo de 15 secondes. Les scènes générées par une API vidéo externe ne sont pas activées. Les nouvelles commandes Sora sont fermées et les soldes historiques conservés.

## Mise à jour d'un VPS existant

Depuis la session administrateur du VPS :

```bash
cd /home/eshelle/app
sudo -u eshelle git pull --ff-only origin main
sudo bash deploy/update_adgen_studio.sh
```

Ne pas exécuter `deploy.sh` ou `deploy/deploy.sh` pour cette mise à jour : ils concernent l'installation générale du serveur.

Le script dédié vérifie les modifications locales et le service, vérifie/installe FFmpeg, sauvegarde la base configurée par Django (SQLite ou PostgreSQL), applique les migrations ciblées, installe un timer de reprise des montages, redémarre Gunicorn et contrôle le catalogue public. La base, `.env`, les médias et la configuration Nginx ne sont pas recréés. Aucun nouvel asset statique n'est ajouté par cette version.

Les commandes Django utilisent le `.env` du projet. Si votre service charge une autre configuration de base, alignez d'abord le contexte d'exécution de ces commandes avec celui du service. Les sauvegardes se trouvent dans `/home/eshelle/backups/adgen-studio/`, accessibles seulement à l'administrateur et au propriétaire applicatif. SQLite est vérifié par `integrity_check` ; PostgreSQL par lecture du catalogue de l'archive. Cela ne remplace pas un exercice complet de restauration.

## Vérifications

```bash
sudo systemctl is-active eshelle eshelle-studio-renders.timer
sudo systemctl list-timers eshelle-studio-renders.timer
sudo -u eshelle .venv/bin/python manage.py showmigrations adgen accounts
sudo -u eshelle .venv/bin/python manage.py studio_economics
```

Parcours connecté à vérifier : `/pub/` → `/pub/studio/audio/` → sélectionner une campagne → générer une narration courte → retour campagne → associer l'audio → créer le montage. Une génération vocale réelle utilise des crédits fournisseur ; les tests automatisés utilisent des simulations.

Les requêtes audio ont un délai fournisseur de 90 secondes, suivi d'une validation de durée bornée à 15 secondes, compatible avec le timeout Gunicorn de 120 secondes décrit dans le dépôt. Vérifier le timeout effectivement utilisé sur le VPS et celui du proxy si l'audio interrompt les requêtes.

## Catalogue et enveloppes de marge

| Offre / 30 jours | XAF | Lots texte | Montages 15 s | Caractères voix | Ambiances |
|---|---:|---:|---:|---:|---:|
| Essentiel | 3 000 | 20 | 5 | 3 000 | 5 |
| Créateur | 10 000 | 100 | 25 | 15 000 | 25 |
| Business | 25 000 | 300 | 80 | 45 000 | 80 |

Quotas sur 30 jours glissants. Les anciens plans conservent leurs prix et limites historiques, mais sont retirés des nouveaux achats. Le clonage et le budget de diffusion publicitaire ne sont pas inclus.

`studio_economics` calcule un scénario à pleine consommation avec des provisions de 5 % pour le paiement, 25 % pour la communication, 20 % pour la gestion et 20 % de réserve sur les coûts techniques. Les soldes estimés avant fiscalité et charges non couvertes sont respectivement 1 045, 2 726 et 5 528 XAF. Ils ne sont pas garantis : remplacer les coûts unitaires du scénario par les factures et les mesures réelles. Le stockage cumulé et le support doivent être suivis.

## Incidents et retour arrière

Si une étape échoue, le script s'arrête : conserver son message et le chemin de sauvegarde. Ne pas inverser les migrations ou restaurer automatiquement une ancienne base après de nouvelles ventes. Les migrations de schéma sont additives : un retour au précédent commit peut généralement conserver ces champs supplémentaires. Restaurer explicitement le catalogue historique si le code précédent ne connaît pas les nouveaux plans, et vérifier les abonnements vendus depuis la publication avant toute décision.

La commande `process_studio_renders` traite les montages en attente et solde les traitements interrompus depuis plus de deux heures. Elle ne relance pas automatiquement les appels payants. L'administration `StudioUsage` permet de vérifier les réservations et les tentatives incertaines.

Tests locaux : `python manage.py test adgen.test_studio adgen.tests --settings=adgen.test_settings --noinput`. Cette configuration utilise une base de test SQLite et aucune clé réelle.
