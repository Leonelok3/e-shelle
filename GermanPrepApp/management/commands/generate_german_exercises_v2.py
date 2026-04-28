"""
Génération d'exercices allemands haute qualité via OpenAI.

Chaque exercice teste RÉELLEMENT la langue allemande avec du contenu en allemand.
Questions en français pour la clarté, mais contenu/réponses en allemand.

Usage :
    # Générer pour tous les niveaux, tous les skills
    python manage.py generate_german_exercises_v2

    # Un niveau spécifique
    python manage.py generate_german_exercises_v2 --level B1

    # Un skill spécifique
    python manage.py generate_german_exercises_v2 --level A1 --skill GRAMMATIK --count 20

    # Régénérer les exercices existants (refresh)
    python manage.py generate_german_exercises_v2 --level B2 --refresh

    # Mode dry-run (affiche les prompts sans appel API)
    python manage.py generate_german_exercises_v2 --level A1 --skill GRAMMATIK --dry-run
"""
import json
import logging
import re
import time

from django.core.management.base import BaseCommand

from GermanPrepApp.models import GermanExam, GermanLesson, GermanExercise
from ai_engine.services.llm_service import call_llm

logger = logging.getLogger(__name__)

ALL_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# ─── DESCRIPTIONS DE NIVEAU ───────────────────────────────────────────────────
LEVEL_DESC = {
    "A1": "débutant — salutations, chiffres, couleurs, famille, présent simple, articles définis/indéfinis",
    "A2": "élémentaire — quotidien, Perfekt, Präteritum (sein/haben/modaux), prépositions courantes",
    "B1": "intermédiaire — verbes à particule, Konjunktiv II (würde+inf, hätte, wäre), subordonnées, Passiv simple",
    "B2": "intermédiaire avancé — Konjunktiv II complet, discours indirect, Passiv Perfekt, registres formel/informel",
    "C1": "avancé — Konjunktiv I (discours indirect académique), nominalisations, connecteurs logiques avancés, style soutenu",
    "C2": "maîtrise — toutes structures, idiomes, style littéraire, nuances sémantiques fines, registres complexes",
}

# ─── PROMPTS SPÉCIALISÉS PAR SKILL ───────────────────────────────────────────
SKILL_PROMPTS = {

"GRAMMATIK": """\
Tu es un professeur d'allemand expert en grammaire germanique.

Génère exactement {count} exercices QCM de GRAMMAIRE ALLEMANDE pour le niveau {level} ({level_desc}).

RÈGLES STRICTES :
1. Chaque question teste UNE règle grammaticale précise en allemand
2. question_text en français (ex: "Complétez la phrase :", "Choisissez la forme correcte :")
3. Les options A/B/C/D DOIVENT contenir des mots/formes ALLEMANDS
4. Varier les structures : déclinaisons, conjugaison, ordre des mots, cas (Nominativ/Akkusativ/Dativ/Genitiv), prépositions avec cas
5. explanation en français, explique la règle grammaticale

EXEMPLES pour {level} :
- "Choisissez le bon article : ___ Hund ist groß." → A) der B) die C) das D) den
- "Conjuguez 'gehen' à la 3e personne : Er ___ zur Schule." → A) geht B) gehen C) gehst D) ging
- "Quel cas après 'mit' ? Ich fahre ___ Bus." → A) dem B) den C) der D) das

Retourne UNIQUEMENT ce JSON (pas de texte autour, pas de ```):
{{
  "exercises": [
    {{
      "question_text": "Question en français avec phrase allemande à trous ou choisir",
      "option_a": "forme allemande A",
      "option_b": "forme allemande B",
      "option_c": "forme allemande C",
      "option_d": "forme allemande D",
      "correct_option": "A",
      "explanation": "Explication de la règle grammaticale en français"
    }}
  ]
}}""",

"WORTSCHATZ": """\
Tu es un professeur d'allemand expert en vocabulaire.

Génère exactement {count} exercices QCM de VOCABULAIRE ALLEMAND pour le niveau {level} ({level_desc}).

RÈGLES STRICTES :
1. Chaque exercice teste du VOCABULAIRE ALLEMAND réel et utile pour ce niveau
2. Varier les types : traduction FR→DE, traduction DE→FR, synonymes allemands, antonymes, mot dans contexte
3. question_text en français OU en allemand (mélanger les deux)
4. Les options DOIVENT contenir des MOTS ALLEMANDS (sauf pour type traduction DE→FR)
5. explanation mentionne le contexte d'utilisation du mot

EXEMPLES pour {level} :
- "Que signifie 'Krankenhaus' en français ?" → A) école B) hôpital C) hôtel D) mairie
- "Quel mot allemand signifie 'travailler' ?" → A) arbeiten B) fahren C) kochen D) wohnen
- "Trouvez le synonyme de 'sprechen' en allemand :" → A) reden B) hören C) schreiben D) lesen
- "Complétez : Das ___ kostet 5 Euro." (un pain) → A) Brot B) Wasser C) Tisch D) Haus

Retourne UNIQUEMENT ce JSON :
{{
  "exercises": [
    {{
      "question_text": "Question sur le vocabulaire allemand",
      "option_a": "option A",
      "option_b": "option B",
      "option_c": "option C",
      "option_d": "option D",
      "correct_option": "B",
      "explanation": "Explication + contexte d'utilisation du mot"
    }}
  ]
}}""",

"HOREN": """\
Tu es un professeur d'allemand expert en compréhension orale (Hören).

Génère exactement {count} exercices de COMPRÉHENSION ORALE SIMULÉE pour le niveau {level} ({level_desc}).

RÈGLES STRICTES :
1. Simuler une mini-transcription audio (dialogue, annonce, message) en ALLEMAND
2. question_text en français : décrit la situation + pose la question de compréhension
3. Inclure le texte allemand "entendu" dans question_text entre guillemets
4. Les options sont en français (car on teste la compréhension)
5. Scenarios réalistes : gare, supermarché, conversation, message vocal, radio

FORMAT question_text :
"Vous entendez à la gare : 'Der Zug nach Berlin hat 20 Minuten Verspätung, wir entschuldigen uns.' Quelle information est donnée ?"

EXEMPLES pour {level} :
- Dialog entre amis, questions sur lieu/heure/prix
- Annonces dans transports/magasins
- Messages téléphoniques
- Bulletins météo courts

Retourne UNIQUEMENT ce JSON :
{{
  "exercises": [
    {{
      "question_text": "Situation + texte allemand entre guillemets + question en français",
      "option_a": "réponse en français A",
      "option_b": "réponse en français B",
      "option_c": "réponse en français C",
      "option_d": "réponse en français D",
      "correct_option": "A",
      "explanation": "Explication basée sur le texte allemand fourni"
    }}
  ]
}}""",

"LESEN": """\
Tu es un professeur d'allemand expert en compréhension écrite (Lesen).

Génère exactement {count} exercices de COMPRÉHENSION ÉCRITE pour le niveau {level} ({level_desc}).

RÈGLES STRICTES :
1. Chaque exercice inclut un TEXTE ÉCRIT EN ALLEMAND dans question_text
2. Le texte est suivi d'une question de compréhension en français
3. Textes variés : email, SMS, annonce, article court, mode d'emploi, menu
4. Longueur du texte adaptée au niveau ({level}) : A1=1-2 phrases, B1=3-5 phrases, C1=6-8 phrases
5. Les options peuvent être en français (on teste la compréhension du texte allemand)

FORMAT question_text :
"Lisez ce message : [TEXTE EN ALLEMAND ICI]\n\nQue veut dire l'auteur ?"

EXEMPLES :
- Email professionnel → question sur l'objet/la demande
- SMS entre amis → question sur le rendez-vous proposé
- Affiche de magasin → question sur les horaires/promotions
- Recette courte → question sur un ingrédient/étape

Retourne UNIQUEMENT ce JSON :
{{
  "exercises": [
    {{
      "question_text": "Texte allemand complet + question de compréhension en français",
      "option_a": "réponse A",
      "option_b": "réponse B",
      "option_c": "réponse C",
      "option_d": "réponse D",
      "correct_option": "C",
      "explanation": "Explication avec référence aux mots/phrases clés du texte"
    }}
  ]
}}""",

"SPRECHEN": """\
Tu es un professeur d'allemand expert en expression orale (Sprechen).

Génère exactement {count} exercices de PRATIQUE ORALE pour le niveau {level} ({level_desc}).
Ces exercices aident à préparer la partie Sprechen des examens (Goethe, telc, TestDaF).

RÈGLES STRICTES :
1. Exercices de type : choisir la bonne réponse orale, formule de politesse, registre approprié
2. question_text décrit une situation de communication en français
3. Les options A/B/C/D sont des PHRASES EN ALLEMAND à dire à voix haute
4. Varier : salutations, demandes, réponses, excuses, négociations, descriptions

FORMAT question_text :
"Vous êtes dans un restaurant. Le serveur vous demande 'Was möchten Sie trinken?'. Que répondez-vous poliment ?"

EXEMPLES :
- Demander le chemin en allemand
- Commander au restaurant/café
- Se présenter formellement vs informellement
- Exprimer une opinion sur un sujet simple

Retourne UNIQUEMENT ce JSON :
{{
  "exercises": [
    {{
      "question_text": "Situation de communication décrite en français",
      "option_a": "phrase allemande A",
      "option_b": "phrase allemande B",
      "option_c": "phrase allemande C",
      "option_d": "phrase allemande D",
      "correct_option": "B",
      "explanation": "Explication du registre, de la politesse et des formules utilisées"
    }}
  ]
}}""",

"SCHREIBEN": """\
Tu es un professeur d'allemand expert en expression écrite (Schreiben).

Génère exactement {count} exercices de COMPÉTENCE ÉCRITE pour le niveau {level} ({level_desc}).

RÈGLES STRICTES :
1. Exercices qui testent la capacité à écrire correctement en allemand
2. Types : choisir la bonne formulation, corriger une phrase, compléter un texte formel
3. question_text en français décrit la tâche
4. Les options DOIVENT être des PHRASES/FORMULES EN ALLEMAND
5. Contextes : emails formels, messages, lettres, formulaires

FORMAT question_text :
"Pour commencer un email formel en allemand à un inconnu, quelle formule utilisez-vous ?"

EXEMPLES :
- Débuter/terminer un email formel ou informel
- Reformuler une phrase de manière plus formelle
- Choisir le bon connecteur logique (weil, obwohl, damit, sodass)
- Corriger une faute dans une phrase allemande

Retourne UNIQUEMENT ce JSON :
{{
  "exercises": [
    {{
      "question_text": "Tâche d'écriture décrite en français",
      "option_a": "formule/phrase allemande A",
      "option_b": "formule/phrase allemande B",
      "option_c": "formule/phrase allemande C",
      "option_d": "formule/phrase allemande D",
      "correct_option": "D",
      "explanation": "Explication de la bonne formule et de son contexte d'utilisation"
    }}
  ]
}}""",
}


def _extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("Aucun JSON trouvé dans la réponse LLM.")
    return json.loads(cleaned[start:end])


def _validate_exercises(data: dict, expected_count: int) -> list:
    if "exercises" not in data or not isinstance(data["exercises"], list):
        raise ValueError("Clé 'exercises' manquante ou invalide.")
    exercises = data["exercises"]
    if len(exercises) == 0:
        raise ValueError("Liste d'exercices vide.")
    for i, ex in enumerate(exercises):
        for f in ("question_text", "option_a", "option_b", "correct_option"):
            if f not in ex:
                raise ValueError(f"Exercice {i}: champ '{f}' manquant.")
        if ex["correct_option"] not in ("A", "B", "C", "D"):
            raise ValueError(f"Exercice {i}: correct_option invalide '{ex['correct_option']}'.")
    return exercises


class Command(BaseCommand):
    help = "Génère des exercices allemands authentiques et pédagogiques via OpenAI"

    def add_arguments(self, parser):
        parser.add_argument("--level", type=str, default=None,
                            help="Niveau CECR : A1..C2. Défaut : tous.")
        parser.add_argument("--skill", type=str, default=None,
                            help="Skill : GRAMMATIK, WORTSCHATZ, HOREN, LESEN, SPRECHEN, SCHREIBEN. Défaut : tous.")
        parser.add_argument("--count", type=int, default=8,
                            help="Exercices par appel (groupe de ~8, défaut: 8)")
        parser.add_argument("--lessons-per-skill", type=int, default=5,
                            help="Nombre de lots d'exercices à générer par skill/niveau (défaut: 5)")
        parser.add_argument("--refresh", action="store_true",
                            help="Régénérer les exercices même si la leçon en a déjà")
        parser.add_argument("--sleep", type=float, default=1.5,
                            help="Pause entre appels API (défaut: 1.5s)")
        parser.add_argument("--continue-on-error", action="store_true",
                            help="Continuer en cas d'erreur API")
        parser.add_argument("--dry-run", action="store_true",
                            help="Affiche les prompts sans appeler l'API")
        parser.add_argument("--exam-type", type=str, default="GOETHE",
                            help="Type d'examen : GOETHE, TELC, TESTDAF (défaut: GOETHE)")

    def handle(self, *args, **options):
        levels = [options["level"].upper()] if options["level"] else ALL_LEVELS
        skills = [options["skill"].upper()] if options["skill"] else list(SKILL_PROMPTS.keys())
        count = options["count"]
        lots = options["lessons_per_skill"]
        refresh = options["refresh"]
        sleep_sec = options["sleep"]
        continue_on_error = options["continue_on_error"]
        dry_run = options["dry_run"]
        exam_type = options["exam_type"].upper()

        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODE DRY-RUN — aucun appel API, aucune insertion."))

        total_created = 0
        total_failed = 0

        for level in levels:
            if level not in ALL_LEVELS:
                self.stderr.write(f"Niveau inconnu : {level}")
                continue

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n▶ Niveau {level}"))

            # Trouver ou créer l'examen de référence pour ce niveau
            from django.utils.text import slugify
            slug = slugify(f"{exam_type}-{level}").lower()
            exam = GermanExam.objects.filter(level=level, is_active=True).first()

            if not exam:
                self.stdout.write(self.style.WARNING(
                    f"  Aucun GermanExam actif pour {level}. "
                    f"Lancez d'abord generate_german_content --level {level}."
                ))
                continue

            for skill in skills:
                if skill not in SKILL_PROMPTS:
                    self.stderr.write(f"Skill inconnu : {skill}")
                    continue

                self.stdout.write(f"  Skill {skill} :")
                prompt_template = SKILL_PROMPTS[skill]
                level_desc = LEVEL_DESC.get(level, level)

                prompt = prompt_template.format(
                    count=count,
                    level=level,
                    level_desc=level_desc,
                )

                if dry_run:
                    self.stdout.write(f"    [DRY-RUN] Prompt généré ({len(prompt)} chars)")
                    self.stdout.write(f"    Aperçu : {prompt[:200]}…")
                    continue

                # Trouver les leçons de ce skill pour cet examen
                lessons = list(GermanLesson.objects.filter(
                    exam=exam, skill=skill
                ).order_by("order")[:lots])

                if not lessons:
                    self.stdout.write(self.style.WARNING(
                        f"    Aucune leçon trouvée pour {level}/{skill}. "
                        f"Créez d'abord des leçons."
                    ))
                    # Générer quand même des exercices standalone en créant une leçon
                    lesson = GermanLesson.objects.create(
                        exam=exam,
                        title=f"Exercices {skill} {level}",
                        skill=skill,
                        order=GermanLesson.objects.filter(exam=exam).count() + 1,
                        intro=f"Exercices de {skill} pour le niveau {level}.",
                        content="",
                    )
                    lessons = [lesson]
                    self.stdout.write(f"    → Leçon créée automatiquement : '{lesson.title}'")

                for lesson in lessons[:lots]:
                    existing = GermanExercise.objects.filter(lesson=lesson).count()
                    if existing > 0 and not refresh:
                        self.stdout.write(
                            f"    ⏭  '{lesson.title}' : {existing} exercices déjà là (--refresh pour régénérer)"
                        )
                        continue

                    self.stdout.write(
                        f"    📝 Génération pour '{lesson.title}'…", ending=" "
                    )
                    self.stdout.flush()

                    try:
                        raw = call_llm(
                            "Tu es un expert en enseignement de l'allemand langue étrangère (DaF). "
                            "Tu génères des exercices pédagogiques de haute qualité. "
                            "Retourne UNIQUEMENT du JSON valide, sans markdown, sans texte autour.",
                            prompt,
                        )
                        data = _extract_json(raw)
                        exercises = _validate_exercises(data, count)

                        if refresh and existing > 0:
                            GermanExercise.objects.filter(lesson=lesson).delete()

                        created_count = 0
                        for ex in exercises[:count]:
                            GermanExercise.objects.create(
                                lesson=lesson,
                                question_text=ex["question_text"],
                                option_a=ex.get("option_a", "")[:255],
                                option_b=ex.get("option_b", "")[:255],
                                option_c=ex.get("option_c", "")[:255],
                                option_d=ex.get("option_d", "")[:255],
                                correct_option=ex["correct_option"],
                                explanation=ex.get("explanation", ""),
                            )
                            created_count += 1

                        total_created += created_count
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ {created_count} exercices créés")
                        )

                    except Exception as exc:
                        total_failed += 1
                        msg = f"❌ ERREUR : {exc}"
                        logger.warning("generate_german_exercises_v2: %s / %s — %s", level, skill, exc)
                        if continue_on_error:
                            self.stdout.write(self.style.WARNING(msg))
                        else:
                            self.stderr.write(msg)
                            raise

                    if sleep_sec > 0:
                        time.sleep(sleep_sec)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Terminé — {total_created} exercices créés, {total_failed} erreur(s)."
        ))
        if not dry_run:
            self.stdout.write(
                "\n📋 Commandes utiles pour vérifier :"
                "\n   python manage.py shell -c \""
                "from GermanPrepApp.models import GermanExercise; "
                "print(GermanExercise.objects.count(), 'exercices total')\""
            )
