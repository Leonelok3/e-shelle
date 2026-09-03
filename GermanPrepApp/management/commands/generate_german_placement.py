"""
Commande Django : génération des questions du test de niveau allemand (placement test).

Usage :
    python manage.py generate_german_placement --questions 30
    python manage.py generate_german_placement --questions 20 --replace
"""
import json
import logging
import re
import time

from django.core.management.base import BaseCommand

from GermanPrepApp.models import GermanPlacementQuestion
from ai_engine.services.llm_service import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Tu es un expert en linguistique allemande et en conception de tests de niveau (placement test).
Tu génères des questions QCM pour évaluer le niveau CECR d'un apprenant en allemand (A1 à C2).

Tu retournes UNIQUEMENT un tableau JSON valide (sans texte avant ou après, sans markdown),
avec la structure exacte :

[
  {
    "question_text": "La question en allemand ou sur la langue allemande",
    "option_a": "Option A",
    "option_b": "Option B",
    "option_c": "Option C",
    "option_d": "Option D",
    "correct_option": "A",
    "level_hint": "A1"
  }
]

Règles :
- Chaque question teste un point précis de grammaire, vocabulaire, ou compréhension
- Les questions doivent couvrir progressivement les niveaux A1 (très facile) -> C2 (très difficile)
- 4 options toujours (A, B, C, D), une seule correcte
- correct_option = "A", "B", "C" ou "D"
- level_hint = niveau approximatif de la question ("A1", "A2", "B1", "B2", "C1", "C2")
- Questions variées : conjugaison, articles, cas, prépositions, vocabulaire, sens, structure de phrase
- JSON strict, pas de commentaires, pas de texte autour
"""

USER_PROMPT_TPL = """\
Génère {count} questions QCM pour un test de niveau d'allemand (A1–C2).

Répartition demandée :
- 5 questions très faciles (A1) : salutations, chiffres, couleurs, verbe sein/haben, articles der/die/das
- 5 questions faciles (A2) : Perfekt avec haben/sein, prépositions simples, vocabulaire quotidien
- 5 questions intermédiaires (B1) : verbes à particule, subordonnées, comparatif/superlatif, Präteritum
- 5 questions intermédiaires avancées (B2) : Konjunktiv II, Passiv, vocabulaire moins courant, nuances
- 5 questions avancées (C1/C2) : Konjunktiv I, discours indirect, idiomes, structures complexes, registres

Chaque question doit être distincte et pédagogiquement pertinente.
"""

FALLBACK_QUESTIONS = [
    {
        "question_text": "Wie sagt man 'Bonjour' auf Deutsch ?",
        "option_a": "Guten Tag",
        "option_b": "Danke",
        "option_c": "Tschüss",
        "option_d": "Bitte",
        "correct_option": "A",
    },
    {
        "question_text": "Choisissez la bonne forme: Ich ___ aus Kamerun.",
        "option_a": "bist",
        "option_b": "bin",
        "option_c": "ist",
        "option_d": "sind",
        "correct_option": "B",
    },
    {
        "question_text": "Quel article convient ? ___ Haus",
        "option_a": "der",
        "option_b": "die",
        "option_c": "das",
        "option_d": "den",
        "correct_option": "C",
    },
    {
        "question_text": "Choisissez la phrase correcte.",
        "option_a": "Ich heiße Paul.",
        "option_b": "Ich heißen Paul.",
        "option_c": "Ich heißt Paul.",
        "option_d": "Ich heißt bin Paul.",
        "correct_option": "A",
    },
    {
        "question_text": "Wie spät ist es? 8:30",
        "option_a": "Es ist halb neun.",
        "option_b": "Es ist halb acht.",
        "option_c": "Es ist acht halb.",
        "option_d": "Es ist neun halb.",
        "correct_option": "A",
    },
    {
        "question_text": "Choisissez le bon auxiliaire au Perfekt: Ich ___ gestern Deutsch gelernt.",
        "option_a": "bin",
        "option_b": "habe",
        "option_c": "wurde",
        "option_d": "werde",
        "correct_option": "B",
    },
    {
        "question_text": "Complétez: Wir fahren ___ Berlin.",
        "option_a": "nach",
        "option_b": "in",
        "option_c": "zu",
        "option_d": "bei",
        "correct_option": "A",
    },
    {
        "question_text": "Quelle phrase est correcte ?",
        "option_a": "Ich möchte einen Kaffee.",
        "option_b": "Ich möchte ein Kaffee.",
        "option_c": "Ich möchten einen Kaffee.",
        "option_d": "Ich möchte eine Kaffee.",
        "correct_option": "A",
    },
    {
        "question_text": "Choisissez la bonne forme du comparatif: groß",
        "option_a": "großer",
        "option_b": "größer",
        "option_c": "am groß",
        "option_d": "großest",
        "correct_option": "B",
    },
    {
        "question_text": "Complétez: Ich bleibe zu Hause, ___ ich krank bin.",
        "option_a": "weil",
        "option_b": "aber",
        "option_c": "oder",
        "option_d": "und",
        "correct_option": "A",
    },
    {
        "question_text": "Choisissez la bonne position du verbe: Ich weiß, dass er morgen ___.",
        "option_a": "kommt",
        "option_b": "kommen",
        "option_c": "kommt er",
        "option_d": "er kommt",
        "correct_option": "A",
    },
    {
        "question_text": "Quel est le Präteritum de 'gehen' ?",
        "option_a": "ging",
        "option_b": "gegangen",
        "option_c": "gehst",
        "option_d": "ginge",
        "correct_option": "A",
    },
    {
        "question_text": "Complétez au Konjunktiv II: Wenn ich Zeit hätte, ___ ich reisen.",
        "option_a": "werde",
        "option_b": "wurde",
        "option_c": "würde",
        "option_d": "war",
        "correct_option": "C",
    },
    {
        "question_text": "Choisissez la forme passive correcte: Der Brief ___ geschrieben.",
        "option_a": "wird",
        "option_b": "ist werden",
        "option_c": "hat",
        "option_d": "wurde sein",
        "correct_option": "A",
    },
    {
        "question_text": "Quelle phrase exprime une concession ?",
        "option_a": "Obwohl es regnet, gehen wir spazieren.",
        "option_b": "Weil es regnet, bleiben wir zu Hause.",
        "option_c": "Wenn es regnet, bleiben wir.",
        "option_d": "Es regnet und wir bleiben.",
        "correct_option": "A",
    },
    {
        "question_text": "Discours indirect: Er sagt, er ___ keine Zeit.",
        "option_a": "habe",
        "option_b": "hat",
        "option_c": "hätte gehabt",
        "option_d": "haben",
        "correct_option": "A",
    },
    {
        "question_text": "Choisissez le connecteur le plus soutenu: ___ der hohen Kosten wurde das Projekt genehmigt.",
        "option_a": "Trotz",
        "option_b": "Weil",
        "option_c": "Denn",
        "option_d": "Und",
        "correct_option": "A",
    },
    {
        "question_text": "Que signifie 'etwas in Kauf nehmen' ?",
        "option_a": "accepter un inconvénient",
        "option_b": "acheter quelque chose",
        "option_c": "refuser une offre",
        "option_d": "oublier une règle",
        "correct_option": "A",
    },
]


def _extract_json(raw: str) -> list:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("Aucun tableau JSON trouvé dans la réponse LLM.")
    return json.loads(cleaned[start:end])


def _validate_questions(data: list) -> None:
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("La réponse doit être un tableau JSON non vide.")
    for i, q in enumerate(data):
        for f in ("question_text", "option_a", "option_b", "option_c", "option_d",
                  "correct_option"):
            if f not in q:
                raise ValueError(f"Question {i}: champ manquant '{f}'")
        if q["correct_option"] not in ("A", "B", "C", "D"):
            raise ValueError(
                f"Question {i}: correct_option='{q['correct_option']}' invalide."
            )


class Command(BaseCommand):
    help = "Génère les questions du test de niveau allemand (placement test) via LLM"

    def add_arguments(self, parser):
        parser.add_argument(
            "--questions",
            type=int,
            default=25,
            help="Nombre de questions à générer (défaut: 25)",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Supprimer toutes les questions existantes avant de générer",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continuer en cas d'erreur LLM",
        )

    def handle(self, *args, **options):
        count = options["questions"]
        replace = options["replace"]
        continue_on_error = options["continue_on_error"]

        if replace:
            deleted, _ = GermanPlacementQuestion.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"  {deleted} question(s) existante(s) supprimée(s).")
            )

        existing = GermanPlacementQuestion.objects.count()
        self.stdout.write(
            f"Questions existantes : {existing}. "
            f"Génération de {count} nouvelles questions..."
        )

        user_prompt = USER_PROMPT_TPL.format(count=count)

        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt)
            data = _extract_json(raw)
            _validate_questions(data)
        except Exception as exc:
            msg = f"Erreur lors de la génération LLM : {exc}"
            if continue_on_error:
                self.stdout.write(self.style.WARNING(msg))
                repeats = (count // len(FALLBACK_QUESTIONS)) + 1
                data = (FALLBACK_QUESTIONS * repeats)[:count]
                self.stdout.write(
                    self.style.WARNING(
                        "Utilisation de la banque locale de secours pour garder le test de niveau actif."
                    )
                )
                _validate_questions(data)
            else:
                self.stderr.write(msg)
                raise

        order_start = existing + 1
        created = 0

        for i, q in enumerate(data):
            try:
                GermanPlacementQuestion.objects.create(
                    question_text=q["question_text"],
                    option_a=q["option_a"][:255],
                    option_b=q["option_b"][:255],
                    option_c=q.get("option_c", "")[:255],
                    option_d=q.get("option_d", "")[:255],
                    correct_option=q["correct_option"],
                    order=order_start + i,
                    is_active=True,
                )
                created += 1
            except Exception as exc:
                logger.warning("Erreur insertion question %d : %s", i, exc)
                if not continue_on_error:
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                f"OK - {created} question(s) de placement créée(s). "
                f"Total : {existing + created} questions."
            )
        )
