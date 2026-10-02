# Leçon et exercice du jour — TCF Canada

La page `/prep/fr/tcf/` présente la séance du jour au-dessus des quatre compétences. `/prep/fr/tcf/du-jour/` propose une courte méthode puis un exercice chronométré avec correction après soumission.

## Contenu et format

Un cycle éditorial de 28 séances alterne compréhension écrite, compréhension orale, expression écrite et expression orale, sur sept thèmes originaux. Le cycle se répète au bout de 28 jours : aucun contenu IA n'est généré lors du chargement d'une page. La date bascule à minuit dans le fuseau Django du serveur (actuellement Africa/Douala), sans tâche cron. Tous les visiteurs ont le même thème quotidien. Les options des QCM sont mélangées de manière déterministe selon la date.

- CE/CO : document original et trois QCM à quatre choix ; cinq minutes est une durée d'entraînement conseillée, pas la durée de l'épreuve complète. L'oral propose une écoute, une transcription après réponse et une lecture dédiée hors des consignes.
- EE : rotation des tâches 1, 2 et 3 avec les limites de 60–120, 120–150 et 120–180 mots. La tâche 3 fournit deux points de vue fictifs à comparer. Vingt minutes est une durée conseillée pour cette tâche isolée ; les trois tâches officielles durent ensemble 60 minutes.
- EO : tâche 3, point de vue sans préparation, 4 min 30. Il s'agit d'une prise de parole individuelle, pas d'une simulation des tâches d'interaction avec un examinateur.

Références vérifiées le 2 octobre 2026 :

- https://www.france-education-international.fr/test/tcf-canada
- https://www.france-education-international.fr/document/tcf-tp-qc-ca-exemple-epreuve-eo
- https://www.france-education-international.fr/document/tcf-tp-qc-ca-exemple-epreuve-ee

## Réponses, chronomètre et IA

La page n'affiche aucune clé de réponse ni preuve dans l'exercice avant soumission. Le serveur calcule les réponses correctes. Le chronomètre conserve son point de départ après rechargement ; les dépassements sont signalés. L'envoi automatique demande JavaScript ; sans JavaScript la soumission manuelle reste disponible et le serveur mesure le temps écoulé. Ce mécanisme est un entraînement, pas un contrôle antifraude certifié.

Les productions et corrections sont conservées dans la session courante du navigateur. Le bouton « Recommencer » ouvre une nouvelle tentative ; une nouvelle journée remplace l'état du jour précédent. La liste des dates terminées est limitée à 31 entrées. Cela n'ajoute pas d'historique permanent au compte ni de migration.

L'IA utilise le coach existant, nécessite une connexion et respecte le quota journalier existant. Les corrigés déjà reçus sont réutilisés sans décompter une nouvelle demande. Aucun appel IA n'est fait à la visite, au démarrage ou à la correction d'un QCM. Une panne IA conserve la production et permet de réessayer. Une estimation pédagogique ne devient pas un score officiel TCF/NCLC.

À l'oral, l'enregistrement facultatif reste sur l'appareil (IndexedDB, un enregistrement courant). Il peut être réécouté et téléchargé. Le microphone est arrêté avant navigation. Une transcription peut être saisie après la fin de la prise de parole, sans modifier le temps de l'exercice. Le coach corrige cette transcription et ne note pas la prononciation ou la fluidité acoustique. Le navigateur doit autoriser le microphone et le stockage pour conserver l'enregistrement.

## Déploiement

Le script `deploy/update_tcf_tef.sh` prépare les sept nouveaux MP3, collecte les fichiers statiques et vérifie la page quotidienne après redémarrage. Les anciens parcours TCF/TEF et droits Premium ne sont pas modifiés ; ce nouveau rendez-vous éditorial est accessible à tous. Le serveur ne copie pas la base locale.

```bash
cd /home/eshelle/app
sudo -u eshelle git pull --ff-only origin main
bash deploy/update_tcf_tef.sh
```

Préparation audio seule : `.venv/bin/python manage.py prepare_tcf_daily_audio`. Les MP3 sont versionnés par le hash de leur texte et réutilisés en cache. Aucune nouvelle dépendance n'est nécessaire.
