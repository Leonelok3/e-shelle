# Navigation Canada — 20 septembre 2026

## Changements

- Navigation commune dans le gabarit principal : Accueil Canada, Mon projet,
  Préparer mon test, Travailler, Étudier et Visiter.
- Liens regroupés par objectif, rubrique active issue des routes Django,
  repère de localisation et menu natif « Tous les modules et assistants IA ».
- Vingt destinations accessibles, dont les coachs immigration et français,
  l’entraînement, la progression et la simulation d’entretien.
- Accueil organisé par objectif ; suppression du catalogue de douze outils
  qui précédait le dossier CV et simplification des colonnes TCF/TEF.
- Même en-tête et pied de page Canada dans la préparation aux tests.
- Aucun changement des modèles, données, API ou services IA.

## Validation locale

- `manage.py check` : aucune erreur.
- 47 tests de régression IA/Canada réussis avec fournisseurs simulés.
- 4 tests supplémentaires de navigation réussis avec les vraies routes et
  le gabarit global, sans remplacement de `base.html`.
- 6 scénarios JavaScript de soumission IA réussis.
- 6 rendus navigateur : accueil, CV et TCF à 1440 et 390 pixels.
  Ouverture/fermeture du menu, vingt liens et absence de débordement horizontal
  vérifiés. Captures dans `output/canada-navigation/`.
- Les rendus visuels utilisent un contexte synthétique, sans connexion à un
  compte utilisateur ni accès aux données. Les ressources externes sont bloquées.
- `git diff --check` : aucune erreur.

## Fournisseurs réels

- Conversation partagée : premier essai en échec (Gemini Vertex et Studio 503),
  deuxième essai réussi. Disponibilité intermittente observée.
- Synthèse/transcription audio : aller-retour réussi sur une phrase synthétique.
- Corrections écrite et orale : deux essais chacun en échec ; secours Anthropic 400.
  Une sonde complémentaire a identifié une erreur de facturation/crédit chez
  Anthropic. Une requête JSON minimale Gemini a réussi, sans pour autant valider
  les corrections complètes. Ces erreurs proviennent des appels réels,
  indépendamment des changements de navigation.
- Les tests automatisés des CV, diagnostics et collectes utilisent des fournisseurs
  simulés : ils ne certifient pas la disponibilité réelle de chaque service.

## Rejouer

```powershell
.\.venv\Scripts\python.exe manage.py test canada_resume.test_navigation --noinput
.\.venv\Scripts\python.exe manage.py test preparation_tests.tests preparation_tests.tests_ai canada_resume.tests jobs.test_canada_validation ai_engine.test_content_fallback --settings=preparation_tests.test_settings --noinput
node scripts/test_preparation_ai_ui.cjs
.\.venv\Scripts\python.exe scripts/check_canada_navigation_visual.py
```

Le contrôle visuel nécessite Playwright et Chromium. `CANADA_TEST_BROWSER` permet
de préciser le chemin d’un exécutable Chromium déjà installé.

Aucun commit ni déploiement effectué. La disponibilité des assistants IA et un
parcours connecté sur l’environnement cible restent à valider avant la production.
