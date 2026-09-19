# Pack E-Shelle : entraînement assisté par IA

Livraison locale du 19 septembre 2026. Point d'entrée connecté : `/prep/fr/mon-coach/`.

## Parcours livré

- Choix TCF/TEF et niveau cible, recommandations parmi les leçons publiées, priorités tirées des dernières corrections et historique personnel.
- Correction écrite et orale avec quatre critères, passages cités, actions concrètes, exercices ciblés, auto-vérification et exemple de réponse. L'évaluation orale sur transcription ne mesure pas la prononciation ou la fluidité acoustique.
- Nouvelle tentative avec comparaison uniquement entre évaluations utilisant la même grille. Le dernier texte et son retour sont restaurés dans la leçon pour leur auteur.
- Explications de QCM fondées sur la réponse de référence enregistrée. Le serveur vérifie la réponse choisie ; une valeur « correct » envoyée par le navigateur ne valide pas un exercice.
- Conversation avec contexte TCF/TEF, conservation des échanges dans la page, compteur de quota actualisé sans rechargement et protection CSRF.
- Affichage des formats d'examen actualisés et distinction entre score d'entraînement, niveau travaillé et résultat officiel. « Objectif C2 » exprime une cible, sans garantie de résultat.
- Feuille de route Canada sourcée : suppression du calcul CRS simplifié trompeur et des anciennes promesses de points liés à une offre d'emploi. Les anciennes feuilles de route non marquées comme révisées ne sont plus présentées comme actuelles.

## Fiabilité et limites

Les corrections exigent des critères numériques valides et une priorité exploitable. Les citations absentes du texte de l'élève sont écartées. Une réponse mal structurée peut être réparée une fois avant le passage au fournisseur suivant ; aucun faux score de remplacement n'est enregistré en cas d'indisponibilité.

Les tests externes ont obtenu une correction écrite détaillée et une évaluation orale avec Gemini. Des réponses fournisseur invalides/intermittentes ont aussi été observées ; Anthropic a renvoyé une erreur 400 et OpenAI n'était pas configuré localement. Cela ne constitue pas une validation de tous les fournisseurs en production. Les explications QCM peuvent revenir au corrigé de référence, explicitement signalé, si le service IA échoue.

Les données historiques sont conservées. Aucune migration de schéma ni modification de base de production n'a été effectuée. Les formats officiels affichés ne transforment pas automatiquement toute la banque existante en sujets officiels : les examens blancs restent des entraînements selon les exercices disponibles. L'IA ne délivre ni certification linguistique ni décision d'immigration.

## Vérification

Suite isolée, base de test temporaire et fournisseurs simulés :

```powershell
.\.venv\Scripts\python.exe manage.py test preparation_tests.tests_learning preparation_tests.tests preparation_tests.tests_ai canada_resume.tests jobs.test_canada_validation ai_engine.test_content_fallback --settings=preparation_tests.test_settings --noinput
.\.venv\Scripts\python.exe manage.py check
node scripts/test_preparation_ai_ui.cjs
.\.venv\Scripts\python.exe scripts/verify_learning_ui.py
```

Les contrôles couvrent confidentialité, validation des productions, contexte d'examen, comparaison des tentatives, recommandations, erreurs fournisseur, références Canada et protection CSRF. Six scénarios JavaScript de soumission sont vérifiés séparément.

La vérification navigateur utilise les vrais templates, CSS et JavaScript, avec données synthétiques et réponses réseau simulées, sur ordinateur et mobile : mise en page, historique, choix de niveau, soumission écrite, exercices de correction et deux échanges de chat. Les captures locales sont dans `output/learning-coach-qa/`. Ces essais ne remplacent pas une recette sur le serveur déployé.

## Sources officielles consultées

- [France Éducation international — TCF Canada](https://www.france-education-international.fr/test/tcf-canada)
- [CCI Paris Île-de-France — déroulement du TEF Canada](https://www.lefrancaisdesaffaires.fr/candidat/test-evaluation-francais/tef-canada/passation/)
- [IRCC — critères du Système de classement global](https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score/crs-criteria.html)
- [IRCC — offre d'emploi et Entrée express](https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/documents/job-offer.html)

Avant une mise en ligne, déployer le code avec les nouveaux fichiers statiques, exécuter la collecte des statiques selon la procédure habituelle du projet et vérifier une correction avec un compte de test sur le serveur. Aucun déploiement n'a été exécuté pour cette livraison.
