# Audit IA Canada — 19 septembre 2026

## Résultat

Les contrôles locaux passent : 47 tests Python, 6 scénarios JavaScript,
`manage.py check`, vérification syntaxique JavaScript et `git diff --check`.
Les tests Django utilisent SQLite en mémoire et des fournisseurs simulés.
Le gabarit global de navigation est remplacé dans ces tests isolés : ce n'est
pas une validation visuelle complète du site.

Des appels réels, avec la configuration locale et des données synthétiques,
ont également réussi :

| Fonction | Contrôle |
| --- | --- |
| Chat partagé des coachs Canada/TCF et des entretiens | Réponse du fournisseur réel |
| Correction écrite en français | Retour structuré du fournisseur réel |
| Évaluation orale en français | Retour réel à partir d'une transcription de test |
| Synthèse et transcription audio | Phrase française générée puis reconnue avec « bonjour » et « examen » |
| CV et lettre Canada | Tests du découpage des documents et du secours local |
| Amélioration des descriptions | Test de la réponse de l'API avec fournisseur simulé |
| Diagnostic Canada | Test de sauvegarde de la feuille de route avec fournisseur simulé |
| Génération TCF et collectes Canada | Tests existants des replis, sources et erreurs |

## Corrections

- Les soumissions écrites/orales enregistraient `EE`/`EO` dans `last_answer`,
  limité à un caractère. Cette écriture est acceptée par SQLite mais peut échouer
  sur PostgreSQL. Utilisation de `E`/`O`, sans migration. C'est une cause compatible
  avec la capture, pas une preuve issue des journaux de production.
- Sauvegarde atomique de la soumission et de sa progression ; une erreur
  d'enregistrement annule l'ensemble. Test de régression dédié.
- En cas d'échec des fournisseurs, les corrections françaises répondent en JSON
  avec HTTP 503 et n'enregistrent pas les notes du secours heuristique.
  L'option stricte est activée uniquement dans les soumissions françaises.
- Une transcription échouée ne retourne plus une phrase fictive présentée
  comme une transcription. Correction du type MIME WAV et limite de temps
  explicite pour l'appel de transcription OpenAI.
- Les entraînements EE/EO de l'ancien moteur renvoient aux leçons avec les
  éditeurs/enregistreurs adaptés, au lieu des choix QCM de remplacement.
- Le JavaScript distingue erreur serveur, session expirée, refus CSRF et panne
  réseau ; le texte saisi reste intact. Version du script actualisée dans la leçon.

## Limites et état des fournisseurs

- Gemini a répondu, mais une erreur 503 et un échec d'évaluation orale ont aussi
  été observés. L'évaluation orale a réussi lors du contrôle suivant.
- OpenAI n'est pas configuré dans l'environnement local.
- Le secours Anthropic a retourné HTTP 400 lors d'un essai ; sa disponibilité
  n'est donc pas validée. Les détails sensibles des erreurs ne sont pas affichés.
- La disponibilité actuelle d'un fournisseur ne garantit pas celle des prochains
  appels. La cause exacte du message de la capture nécessite les journaux serveur.
- Aucun déploiement, aucune migration et aucune écriture dans les données des
  utilisateurs. Les changements IA préexistants ont été conservés ; seules les
  corrections décrites ci-dessus ont été ajoutées au service d'évaluation.
- Le parcours connecté sur e-shelle.com reste à vérifier après déploiement.

## Rejouer les contrôles

```powershell
.\.venv\Scripts\python.exe manage.py test preparation_tests.tests preparation_tests.tests_ai canada_resume.tests jobs.test_canada_validation ai_engine.test_content_fallback --settings=preparation_tests.test_settings --noinput
node scripts/test_preparation_ai_ui.cjs
.\.venv\Scripts\python.exe manage.py check
```

Les commandes suivantes appellent réellement les fournisseurs avec des données
de test et peuvent consommer leur quota :

```powershell
.\.venv\Scripts\python.exe scripts/audit_canada_providers.py
.\.venv\Scripts\python.exe scripts/audit_canada_providers.py --chat
.\.venv\Scripts\python.exe scripts/audit_canada_providers.py --audio
.\.venv\Scripts\python.exe scripts/audit_canada_providers.py --oral
```
