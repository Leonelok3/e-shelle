# Immigration97 — parcours et validation locale

## Changements

- Identité Immigration97, accueil refait et cinq rubriques : Mon parcours, Apprendre avec l’IA, Mon coach IA, Mon dossier Canada, Opportunités. L’accueil reste accessible séparément ; les 24 liens de modules sont regroupés dans le menu détaillé.
- Objectif, examen, niveau de travail, niveau visé et rythme enregistrés par compte. Bilan original de huit questions de lecture/grammaire, explicitement indicatif ; son résultat n’est appliqué au niveau de travail qu’après validation de l’utilisateur.
- Tableau de bord utilisant les leçons publiées et la progression existante, programme conseillé sur sept jours, difficultés à reprendre et checklist personnelle. Les niveaux sans cours publié sont annoncés comme tels.
- Brouillons écrits enregistrés par utilisateur/exercice. Restauration automatique, sauvegarde différée et message explicite en cas d’échec sans effacer le texte présent.
- Limite quotidienne persistante commune aux trois chats, aux corrections EE/EO et aux explications de réponses. `IMMIGRATION97_DAILY_AI_LIMIT` vaut 20 par défaut. Les entrées rejetées en 4xx sont remboursées ; les tentatives échouées chez le fournisseur restent comptées. Ce plafond de demandes ne constitue pas un plafond de facturation en dollars et ne couvre pas tous les autres générateurs du site.
- Suppression des anciens compteurs de chat liés à la session et protection CSRF des deux chats Canada.
- Correction du basculement Google des évaluations : une requête AI Studio échouée peut désormais être reprise via Vertex. Les échecs ne sont pas transformés en notes inventées.

## Validation

- 76 tests parcours/formation/Canada/jobs/fallback réussis ; ajout ultérieur du test de basculement Studio vers Vertex validé avec les 14 tests ciblés incluant les sept tests du parcours.
- 16 tests navigation et suppression du fournisseur Anthropic réussis.
- Six scénarios JavaScript de soumission IA réussis ; syntaxe du script de brouillons vérifiée.
- Navigateur Chromium : accueil, CV, TCF, onboarding et parcours aux largeurs 1440 et 390 px ; ouverture du menu, 24 liens et absence de débordement horizontal vérifiés. Contextes synthétiques, sans données personnelles.
- Navigateur : restauration, sauvegarde et conservation du texte après une erreur serveur de brouillon validées.
- Appels réels : correction écrite structurée puis correction orale sur transcription synthétique réussies après ajout du basculement Google. Il ne s’agit pas d’une garantie de disponibilité future. La chaîne audio avait été vérifiée séparément auparavant.
- Migrations locales `canada_resume.0006` et `ai_engine.0002` appliquées après sauvegarde SQLite vérifiée dans `output/backups/`. Aucun changement de modèle restant détecté.

## Limites et livraison

La clé OpenAI reste absente de la configuration locale. Un solde sur le compte OpenAI n’active pas automatiquement cette intégration. Aucun secret n’est inscrit dans ce rapport. Gemini a présenté des erreurs 503 pendant les essais ; le basculement a permis la réussite des corrections.

Les changements restent locaux, sans commit ni déploiement dans cette étape. Les migrations, les paramètres IA du serveur et les parcours authentifiés devront être validés sur l’environnement de livraison avant mise en production. Les estimations de langue et le dossier de préparation ne constituent ni un résultat officiel de test ni une décision d’admissibilité IRCC.
