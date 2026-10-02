# Qualité TCF/TEF : corrections et exploitation

Les parcours, URLs, droits Premium, résultats et historiques restent compatibles. Aucun changement de schéma ni migration n'est nécessaire.

## Scripts et audios

Pour la compréhension orale, `CourseExercise.document_text` conserve le document sonore indépendant de la consigne. Les préfixes historiques explicitement reconnus permettent de récupérer une transcription. Une consigne, une question ou un cours méthodologique n'est jamais sélectionné automatiquement comme script.

La génération utilise toujours gTTS : aucune nouvelle clé, aucun fournisseur payant. Le cache inclut la langue et une version ; les fichiers anciens restent présents. Les nouveaux fichiers sont publiés atomiquement après une génération non vide. Cela ne constitue pas une validation acoustique : il faut écouter les fichiers avant de certifier la qualité des voix, la prononciation ou le niveau.

En entraînement, la transcription est repliée et respecte les droits audio existants. Une écoute manquante est annoncée clairement ; un exercice de lecture n'est pas présenté comme une mesure de compréhension orale.

```powershell
.\.venv\Scripts\python.exe manage.py generate_exercise_audio --exam tcf --dry-run
.\.venv\Scripts\python.exe manage.py generate_exercise_audio --exam tcf
```

Les références existantes sont préservées sauf avec `--all`. L'ancien comportement de `fix_co_audio` qui lit `content_html` exige désormais `--legacy-lesson-script`, après vérification humaine du contenu du cours.

## Français et réponses

`repair_french_encoding` simule par défaut. `--apply` sauvegarde toutes les valeurs avant modification dans `output/tcf_tef_quality`, puis applique une transaction avec vérification des modifications concurrentes. Les corrections d'accents lexicaux et des clés QCM se limitent au lot de démonstration `tcf-advanced-*` identifiable. Aucune correction linguistique arbitraire des autres contenus n'est inventée.

```powershell
.\.venv\Scripts\python.exe manage.py repair_french_encoding --exam tcf
.\.venv\Scripts\python.exe manage.py repair_french_encoding --exam tcf --apply
.\.venv\Scripts\python.exe manage.py audit_learning_materials --exam tcf --all-levels --check-audio-files
```

Le générateur demande du français accentué et des explications fondées sur le document. Il rejette les scripts vides et les options absentes, trop longues ou dupliquées avant publication. Ces contrôles ne remplacent pas la relecture pédagogique des réponses produites par l'IA.

## Périmètre local

Les corrections et les audios générés dans cette intervention concernent `db.sqlite3` et `media` du workspace. Aucun déploiement sur le serveur distant n'a été effectué. Les rapports locaux ne décrivent pas nécessairement la base de production.

Le lot local comporte beaucoup de leçons sans exercices et de questions répétées. Les cinq scripts de démonstration repris entre plusieurs thèmes ne constituent pas une banque complète B2/C1/C2. Les intitulés de niveau existants ont été conservés ; leur calibrage reste à valider. Aucun contenu n'a été supprimé, aucun historique n'a été recalculé. Le coach IA et le suivi existants sont réutilisés ; aucune conversation vocale temps réel n'a été ajoutée.

## Vérification

Les tests utilisent une base en mémoire et des fournisseurs simulés : séparation consigne/script, accents HTML/Unicode, réparation avec sauvegarde, clés du lot de démonstration, audit sans écriture, cache par langue, échec audio sans fichier partiel, absence de modification en simulation, documents de lecture et coaching existants.

## Mise à jour du VPS existant

Depuis la session SSH root :

```bash
cd /home/eshelle/app
sudo -u eshelle git pull --ff-only origin main
bash deploy/update_tcf_tef.sh
```

Le script vérifie le service, sauvegarde la base configurée (SQLite ou PostgreSQL), applique les migrations déjà présentes de preparation_tests si nécessaire, répare les textes TCF/TEF et régénère les audios uniquement lorsque le script est identifié. Il conserve les anciennes références si la génération échoue, s'arrête sur une erreur de génération, écrit les audits, redémarre E-Shelle et vérifie la page TCF. Il utilise gTTS et nécessite une connexion réseau sortante. Aucune nouvelle dépendance ni modification de Nginx n'est introduite. Les fichiers locaux et la base locale ne sont pas transférés sur le VPS.

Les sauvegardes de déploiement sont dans `/home/eshelle/backups/tcf-tef/`. Les valeurs avant correction des textes sont aussi journalisées dans `output/tcf_tef_quality/`. Les autres applications ne sont pas migrées par ce script.
