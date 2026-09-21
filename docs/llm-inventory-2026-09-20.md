# Inventaire LLM et retrait d’Anthropic — 20 septembre 2026

## Fournisseurs et modèles trouvés

| Fournisseur | Modèles présents dans le code/configuration | Principaux usages |
| --- | --- | --- |
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `gpt-4.1-mini` | Assistant central, chat, mémoire, anglais, contenu, corrections, outils marketing |
| Google Gemini, via AI Studio et Vertex AI | `gemini-3.6-flash`, `gemini-flash-latest`, `gemini-2.5-flash` | Canada, langues, collectes, AdGen, génération de contenu, VideoStory |
| Ollama/Mistral | Paramètres `OLLAMA_MODEL=mistral` encore présents dans le sous-projet vidéo | Configuration héritée : le client `videostory_local_ai/agents/local_llm.py` appelle actuellement Gemini |
| Anthropic — retiré | Anciennes références Haiku, Sonnet et Opus | Les intégrations actives ont été remplacées par OpenAI/Gemini |

Les noms ci-dessus décrivent le dépôt, pas une garantie de disponibilité des modèles.
Les références Gemini 1.5/2.0 présentes dans le code de compatibilité sont des
identifiants remappés. Les modèles d’image, vidéo et voix ne sont pas des LLM texte
et n’ont pas été modifiés.

## Configuration locale constatée

- OpenAI : aucune clé dans le `.env` principal ni dans l’environnement du processus.
- Google AI Studio : clé configurée ; Vertex AI : fichier d’identifiants présent.
- `deploy/env.production` contient un exemple de clé OpenAI, pas une clé utilisable.
- Le sous-projet vidéo ne fournit pas non plus de clé OpenAI réutilisable.
- Le crédit montré sur la capture appartient au compte OpenAI ; le dépôt local
  doit disposer d’une clé de ce compte pour l’utiliser. Aucun secret affiché.
- Aucun contrôle de la configuration du serveur de production distant effectué.

`scripts/audit_llm_configuration.py` permet de refaire ce contrôle sans afficher
les valeurs des clés et sans appeler les fournisseurs.

## Retrait effectué

- Suppression des appels/imports Anthropic dans les corrections et l’entraînement,
  le générateur SSE, les slides, AdGen, les commandes de mathématiques, les agents
  Facebook, WhatsApp et commercial.
- Réutilisation du service OpenAI/Gemini commun pour les générations textuelles.
- Génération SSE réellement progressive avec OpenAI ou Gemini. Changement de
  fournisseur autorisé uniquement avant le premier texte reçu, pour éviter de
  mélanger deux réponses après une interruption.
- Conservation des contrats JSON/texte, des secours locaux existants et de
  l’historique. Le modèle et les tokens enregistrés proviennent du fournisseur.
- Suppression de la dépendance dans `requirements.txt`, du réglage Django,
  de l’entrée dans `.env`, du modèle de configuration de production et des scripts
  de déploiement. Ces scripts n’ont pas été exécutés.
- Documentation de configuration mise à jour. Les audits historiques et la
  migration initiale sont conservés ; `ClaudeBot` est un nom de robot SEO et
  n’est pas une intégration LLM.
- Migration `ai_engine/0002_generationia_provider_neutral_default.py` : défaut du
  champ modèle rendu neutre. Aucune réécriture des anciens enregistrements.
  Migration préparée, non appliquée à la base locale ni à la production.

## Vérifications

131 tests Python réussis dans les suites exécutées :

- Canada, corrections, apprentissage et replis : 69.
- Contrats des intégrations migrées (y compris mathématiques, SSE, slides,
  Facebook, WhatsApp, AdGen et commercial) : 12.
- Navigation Canada : 4.
- AdGen : 32.
- Livraison WhatsApp : 10.
- Vérification WhatsApp de l’agent commercial : 4.

`manage.py check`, analyse syntaxique des fichiers Python modifiés,
`makemigrations ai_engine --check --dry-run` et `git diff --check` passent.
Les tests utilisent des fournisseurs simulés et n’envoient aucun message.

Appels réels avec contenu synthétique :

- Conversation partagée via Gemini : réussie.
- Streaming Gemini avec métadonnées : réussi.
- Correction écrite complète : encore en échec côté Gemini.
- OpenAI réel : non testé, car la clé locale manque.

La suppression d’Anthropic est terminée dans le dépôt et la configuration locale.
Elle ne certifie pas la disponibilité permanente des fournisseurs restants.
Aucun commit, envoi de message, publication, migration de données ou déploiement.

Référence d’implémentation du streaming OpenAI :
https://developers.openai.com/api/docs/guides/streaming-responses
