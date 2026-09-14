# Contenu Canada et Allemagne : fonctionnement avec ou sans crédit IA

Le mode par défaut est `auto`. Les générateurs de texte essaient OpenAI, puis les clients Gemini configurés. Un appel réussi utilise le compte et la facturation du fournisseur concerné. Une clé API ne permet pas de connaître son solde : le système utilise la réponse réelle de l’API, sans inventer de compteur de crédits. Les abonnements et limites des utilisateurs E-Shelle restent applicables.

Si les fournisseurs échouent (clé absente, quota, panne, réponse vide), les parcours couverts utilisent un repli adapté. Les appels répétés sont temporairement suspendus : 5 minutes pour un problème de quota/authentification, 30 secondes pour une autre erreur. Après ce délai, une nouvelle demande retente l’IA. Le cache Django configuré porte cette suspension ; un cache mémoire local ne la partage pas entre les processus.

| Parcours | Sans IA |
|---|---|
| CV Canada et Allemagne | CV HTML et lettre construits avec les informations saisies, sans qualification inventée. Les descriptions saisies restent dans leur langue d’origine ; aucune traduction automatique n’est prétendue. |
| Description professionnelle | Mise en forme des éléments saisis en puces. |
| Coach Canada et feuille de route | Guide général avec lien IRCC ; aucune décision d’admissibilité. |
| Entretiens | Questions guidées successives ; bilan allemand sans note ni correction individuelle fictive. |
| Offres Canada | Import direct Guichet-Emplois déjà présent, conservé sans dépendance IA. |
| Offres Allemagne | Import direct Bundesagentur ; fiche pratique fondée sur les champs de l’offre. Les fiches locales peuvent ensuite être enrichies par la tâche IA. |
| Actualités Canada | Flux officiel IRCC, puis recherche de pages officielles. Date publiée réelle, sans remplacer une ancienne date par celle du jour. |
| Bourses Canada | Pages de programmes EduCanada ; critères et échéances inconnus renvoient explicitement à la source. |
| Événements Canada | Un événement doit fournir des dates valides et un lieu au Canada dans ses données structurées. Aucun événement inventé pour remplir le catalogue. |
| Leçons allemand et TCF | Banque locale originale A1–C2, avec atelier ciblé et corrigé. Un atelier par niveau/compétence ; les relances ne dupliquent pas la banque pour atteindre artificiellement un nombre demandé. |
| Placement allemand | Banque existante de questions uniques si l’IA échoue ; pas de répétitions pour gonfler le test. |
| Audio TCF | Synthèse vocale existante sans crédit LLM ; en cas d’échec, transcription et consigne adaptée. |

La banque locale est un socle d’entraînement fini, pas un remplacement de tout le programme ni des examens officiels. Les imports PDF arbitraires ne sont pas couverts par une extraction locale. Les bourses Allemagne conservent leur catalogue existant : ce changement ne crée pas d’importeur DAAD. L’accès aux sources et à la synthèse vocale nécessite Internet, même sans crédit IA. Si aucune source vérifiable ne répond, la commande de collecte signale un échec ; les anciennes données ne sont pas remplacées par des inventions. Les règles existantes de masquage des contenus périmés restent en vigueur.

Sources : [communiqués IRCC](https://www.canada.ca/fr/immigration-refugies-citoyennete/nouvelles.html), [catalogue EduCanada](https://www.educanada.ca/scholarships-bourses/non_can/index.aspx?lang=fra).

## Déploiement

Depuis une session SSH sur le VPS, avec le code poussé sur `main` :

```bash
cd /home/eshelle/app
sudo -u eshelle git pull --ff-only origin main
sudo bash deploy/update_content.sh
```

Pas de migration de modèle ni de dépendance supplémentaire pour ce changement. Le script vérifie les générateurs locaux, collecte les statiques et redémarre E-Shelle ainsi que ses unités Celery lorsqu’elles sont installées. Il n’effectue pas de collecte externe ni d’appel payant de génération. Si les services portent d’autres noms, les redémarrer également.

Pour reprendre le déploiement Love précédemment arrêté par une permission de sauvegarde :

```bash
sudo bash deploy/update_love.sh
```

Son dossier `/home/eshelle/love-backups` est maintenant créé avec propriétaire `eshelle` et droits `700`, avant la sauvegarde. La migration reste conditionnée à une sauvegarde réussie.

## Vérifications et exploitation

```bash
sudo -u eshelle .venv/bin/python manage.py check_content_generation
# Après recharge : facultatif, sinon attendre la fin du délai de suspension.
sudo -u eshelle .venv/bin/python manage.py check_content_generation --reset-cooldown
# Collecte réelle sans aucun appel IA :
sudo -u eshelle .venv/bin/python manage.py fetch_canada_jobs --skip-ai --pages 1
sudo -u eshelle .venv/bin/python manage.py fetch_canada_news --skip-ai
sudo -u eshelle .venv/bin/python manage.py fetch_canada_scholarships --skip-ai
sudo -u eshelle .venv/bin/python manage.py fetch_canada_visitor_opps --skip-ai
```

Retirer `--skip-ai` pour rétablir le complément IA des collectes. Pour forcer toutes les générations de texte couvertes sans fournisseur payant, définir `AI_CONTENT_MODE=offline` dans l’environnement du processus ; `auto` est la valeur par défaut. Exemple borné, qui écrit une leçon locale en base :

```bash
sudo -u eshelle env AI_CONTENT_MODE=offline .venv/bin/python manage.py generate_german_content --level B1 --skill LESEN --lessons 1 --sleep 0
sudo -u eshelle env AI_CONTENT_MODE=offline .venv/bin/python manage.py generate_tcf_content --level B1 --section ce --lessons 1 --sleep 0
```

Le contrôle local ne prouve ni que le solde fournisseur est positif ni que les sources externes répondent aujourd’hui. Après déploiement, vérifier une génération de CV, une conversation guidée, une offre et les journaux des collectes. Les tests automatisés utilisent une base SQLite isolée et des fournisseurs simulés :

```bash
python manage.py test ai_engine.test_content_fallback canada_resume.tests --settings=ai_engine.test_content_settings --noinput
```
