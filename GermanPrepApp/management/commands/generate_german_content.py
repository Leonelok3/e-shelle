"""
Commande Django : génération de leçons et exercices allemands via LLM.

Usage :
    python manage.py generate_german_content --level A1 --exam_type GOETHE --lessons 25
    python manage.py generate_german_content --level B1 --skill GRAMMATIK --lessons 10
    python manage.py generate_german_content --level A1 --exercises 8
    python manage.py generate_german_content  # tous les niveaux
"""
import json
import logging
import re
import time

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from GermanPrepApp.models import GermanExam, GermanExercise, GermanLesson
from ai_engine.services.llm_service import call_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt système — expert pédagogique allemand
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
Tu es un expert pédagogique spécialisé dans l'enseignement de la langue allemande.
Tu génères du contenu pédagogique de haute qualité pour une plateforme de préparation
aux examens d'allemand (Goethe-Zertifikat, telc Deutsch, TestDaF, DSH, tests d'intégration).

Tu retournes UNIQUEMENT un objet JSON valide (sans texte avant ou après, sans balise markdown),
avec la structure exacte suivante :

{
  "title": "Titre de la leçon en allemand",
  "intro": "Courte introduction (2-3 phrases) expliquant l'objectif de la leçon en français",
  "content": "Contenu pédagogique complet en HTML simple (<h3>, <p>, <ul>, <li>, <strong>, <em>). Inclure règles, exemples de phrases allemandes avec traduction, astuces.",
  "exercises": [
    {
      "question_text": "Question (en allemand ou sur la langue allemande)",
      "option_a": "Option A",
      "option_b": "Option B",
      "option_c": "Option C",
      "option_d": "Option D",
      "correct_option": "A",
      "explanation": "Explication de la bonne réponse en français"
    }
  ]
}

Règles impératives :
- Adapter rigoureusement au niveau CECR indiqué
- 4 options par exercice (A, B, C, D), une seule correcte
- correct_option = "A", "B", "C" ou "D" uniquement
- Contenu HTML sans balises <html>, <head>, <body>
- JSON strict, pas de commentaires, pas de texte autour
"""

# ---------------------------------------------------------------------------
# Données de référence
# ---------------------------------------------------------------------------
SKILL_LABELS = {
    "GRAMMATIK": "Grammatik (Grammaire)",
    "WORTSCHATZ": "Wortschatz (Vocabulaire)",
    "HOREN": "Hören (Compréhension orale)",
    "LESEN": "Lesen (Compréhension écrite)",
    "SPRECHEN": "Sprechen (Expression orale)",
    "SCHREIBEN": "Schreiben (Expression écrite)",
}

EXAM_TYPE_LABELS = {
    "GOETHE": "Goethe-Zertifikat",
    "TELC": "telc Deutsch",
    "TESTDAF": "TestDaF",
    "DSH": "DSH",
    "GENERAL": "Général / Visa",
    "INTEGRATION": "Test d'intégration",
}

LEVEL_DESCRIPTIONS = {
    "A1": (
        "débutant absolu — phrases très simples, vocabulaire de base "
        "(salutations, chiffres, couleurs, famille, quotidien immédiat)"
    ),
    "A2": (
        "élémentaire — communication simple du quotidien, phrases courtes, "
        "présent/passé composé (Perfekt), vocabulaire courant 700-1000 mots"
    ),
    "B1": (
        "intermédiaire — textes courts sur sujets familiers, verbes à particule, "
        "subordonnées simples, Präteritum, Konjunktiv II de base"
    ),
    "B2": (
        "intermédiaire avancé — textes plus longs et nuancés, Konjunktiv II complet, "
        "structures complexes, registres formel/informel, argumentation"
    ),
    "C1": (
        "avancé — textes académiques et professionnels, Konjunktiv I (discours indirect), "
        "style soutenu, connecteurs logiques avancés, nuances lexicales"
    ),
    "C2": (
        "maîtrise quasi-native — textes très complexes, style littéraire et rhétorique, "
        "toutes les structures grammaticales, idiomes et expressions figées"
    ),
}

# Distribution des leçons par skill pour N leçons totales
# Proportions : GRAMMATIK 28%, WORTSCHATZ 20%, HOREN 20%, LESEN 20%, SPRECHEN 8%, SCHREIBEN 4%
SKILL_WEIGHTS = [
    ("GRAMMATIK", 0.28),
    ("WORTSCHATZ", 0.20),
    ("HOREN", 0.20),
    ("LESEN", 0.20),
    ("SPRECHEN", 0.08),
    ("SCHREIBEN", 0.04),
]

ALL_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_skill_plan(total_lessons: int, only_skill: str | None) -> list[tuple[str, int]]:
    """Retourne une liste [(skill, count), ...] selon le plan de distribution."""
    if only_skill:
        return [(only_skill, total_lessons)]

    plan = []
    assigned = 0
    items = list(SKILL_WEIGHTS)
    for i, (skill, weight) in enumerate(items):
        if i == len(items) - 1:
            count = max(1, total_lessons - assigned)
        else:
            count = max(1, round(total_lessons * weight))
        plan.append((skill, count))
        assigned += count

    return plan


def _get_or_create_exam(level: str, exam_type: str) -> GermanExam:
    """Récupère ou crée un GermanExam pour ce niveau + type."""
    exam_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)
    title = f"{exam_label} {level}"
    slug_base = slugify(f"{exam_type}-{level}").lower()

    exam, created = GermanExam.objects.get_or_create(
        slug=slug_base,
        defaults={
            "title": title,
            "short_description": (
                f"Préparation {exam_label} niveau {level} — "
                f"leçons et exercices en allemand."
            ),
            "description": (
                f"Ce parcours couvre toutes les compétences nécessaires "
                f"pour le {exam_label} niveau {level} : "
                f"Hören, Lesen, Sprechen, Schreiben, Grammatik, Wortschatz."
            ),
            "exam_type": exam_type,
            "level": level,
            "is_active": True,
        },
    )
    return exam, created


def _extract_json(raw: str) -> dict:
    """Extrait et parse le JSON depuis la réponse LLM (robuste aux backticks)."""
    # Retire les balises markdown ```json ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

    # Cherche le premier { ... }
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("Aucun JSON trouvé dans la réponse LLM.")

    return json.loads(cleaned[start:end])


def _validate_lesson(data: dict, exercises_count: int) -> None:
    """Valide la structure JSON de la leçon."""
    for field in ("title", "intro", "content", "exercises"):
        if field not in data:
            raise ValueError(f"Champ manquant : '{field}'")

    exercises = data["exercises"]
    if not isinstance(exercises, list) or len(exercises) == 0:
        raise ValueError("exercises doit être une liste non vide.")

    for i, ex in enumerate(exercises[:exercises_count]):
        for f in ("question_text", "option_a", "option_b", "option_c", "option_d",
                  "correct_option", "explanation"):
            if f not in ex:
                raise ValueError(f"Exercice {i}: champ manquant '{f}'")
        if ex["correct_option"] not in ("A", "B", "C", "D"):
            raise ValueError(
                f"Exercice {i}: correct_option='{ex['correct_option']}' invalide."
            )


def _build_user_prompt(
    level: str, skill: str, exam_type: str, exercises_count: int, lesson_order: int
) -> str:
    skill_label = SKILL_LABELS.get(skill, skill)
    exam_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)
    level_desc = LEVEL_DESCRIPTIONS.get(level, level)

    return (
        f"Génère la leçon n°{lesson_order} pour le niveau {level} ({level_desc}).\n"
        f"Compétence : {skill_label}.\n"
        f"Examen cible : {exam_label}.\n"
        f"Nombre d'exercices QCM à inclure : {exercises_count}.\n\n"
        f"Choisis un sujet pertinent et non répétitif pour ce niveau et cette compétence. "
        f"La leçon doit être pédagogique, bien structurée et directement utile "
        f"pour préparer l'{exam_label} {level}."
    )


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Génère des leçons et exercices allemands via LLM pour GermanPrepApp"

    def add_arguments(self, parser):
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Niveau CECR : A1, A2, B1, B2, C1, C2. Si absent, génère pour tous.",
        )
        parser.add_argument(
            "--exam_type",
            type=str,
            default="GOETHE",
            help="Type d'examen : GOETHE, TELC, TESTDAF, DSH, GENERAL, INTEGRATION (défaut: GOETHE)",
        )
        parser.add_argument(
            "--lessons",
            type=int,
            default=25,
            help="Nombre total de leçons à générer par niveau (défaut: 25)",
        )
        parser.add_argument(
            "--exercises",
            type=int,
            default=5,
            help="Nombre d'exercices QCM par leçon (défaut: 5)",
        )
        parser.add_argument(
            "--skill",
            type=str,
            default=None,
            help=(
                "Skill spécifique : GRAMMATIK, WORTSCHATZ, HOREN, LESEN, SPRECHEN, SCHREIBEN. "
                "Si absent, distribue sur tous les skills."
            ),
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=1.5,
            help="Pause en secondes entre les appels LLM (défaut: 1.5)",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continuer en cas d'erreur LLM ou de parsing JSON",
        )

    def handle(self, *args, **options):
        level_arg = options["level"]
        exam_type = options["exam_type"].upper()
        total_lessons = options["lessons"]
        exercises_count = options["exercises"]
        only_skill = options["skill"].upper() if options["skill"] else None
        sleep_sec = options["sleep"]
        continue_on_error = options["continue_on_error"]

        # Validation
        valid_exam_types = list(EXAM_TYPE_LABELS.keys())
        if exam_type not in valid_exam_types:
            self.stderr.write(
                f"exam_type invalide : '{exam_type}'. Valides : {valid_exam_types}"
            )
            return

        if only_skill and only_skill not in SKILL_LABELS:
            self.stderr.write(
                f"skill invalide : '{only_skill}'. Valides : {list(SKILL_LABELS.keys())}"
            )
            return

        levels = [level_arg.upper()] if level_arg else ALL_LEVELS

        for level in levels:
            if level not in ALL_LEVELS:
                self.stderr.write(f"Niveau inconnu : '{level}'. Ignoré.")
                continue
            self._generate_for_level(
                level=level,
                exam_type=exam_type,
                total_lessons=total_lessons,
                exercises_count=exercises_count,
                only_skill=only_skill,
                sleep_sec=sleep_sec,
                continue_on_error=continue_on_error,
            )

        self.stdout.write(self.style.SUCCESS("✅ Génération terminée."))

    def _generate_for_level(
        self,
        level: str,
        exam_type: str,
        total_lessons: int,
        exercises_count: int,
        only_skill: str | None,
        sleep_sec: float,
        continue_on_error: bool,
    ):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n▶ Niveau {level} — {EXAM_TYPE_LABELS.get(exam_type, exam_type)} "
                f"({total_lessons} leçons)"
            )
        )

        # Créer ou récupérer l'examen
        exam, created = _get_or_create_exam(level, exam_type)
        action = "Créé" if created else "Existant"
        self.stdout.write(f"  {action} : GermanExam '{exam.title}' (slug={exam.slug})")

        # Plan de distribution des skills
        skill_plan = _build_skill_plan(total_lessons, only_skill)
        self.stdout.write(
            f"  Distribution : {', '.join(f'{s}×{n}' for s, n in skill_plan)}"
        )

        # Ordre de départ (évite d'écraser les leçons existantes)
        existing_count = GermanLesson.objects.filter(exam=exam).count()
        lesson_order = existing_count + 1

        generated = 0
        failed = 0

        for skill, count in skill_plan:
            self.stdout.write(f"\n  Skill : {SKILL_LABELS[skill]} ({count} leçons)")

            for i in range(1, count + 1):
                self.stdout.write(
                    f"    [{lesson_order}] Génération leçon {i}/{count}…", ending=" "
                )
                self.stdout.flush()

                user_prompt = _build_user_prompt(
                    level=level,
                    skill=skill,
                    exam_type=exam_type,
                    exercises_count=exercises_count,
                    lesson_order=lesson_order,
                )

                try:
                    raw = call_llm(SYSTEM_PROMPT, user_prompt)
                    data = _extract_json(raw)
                    _validate_lesson(data, exercises_count)

                    lesson = GermanLesson.objects.create(
                        exam=exam,
                        title=data["title"][:255],
                        skill=skill,
                        order=lesson_order,
                        intro=data.get("intro", "")[:500],
                        content=data.get("content", ""),
                    )

                    exo_list = data["exercises"][:exercises_count]
                    for exo_data in exo_list:
                        GermanExercise.objects.create(
                            lesson=lesson,
                            question_text=exo_data["question_text"],
                            option_a=exo_data["option_a"][:255],
                            option_b=exo_data["option_b"][:255],
                            option_c=exo_data.get("option_c", "")[:255],
                            option_d=exo_data.get("option_d", "")[:255],
                            correct_option=exo_data["correct_option"],
                            explanation=exo_data.get("explanation", ""),
                        )

                    generated += 1
                    lesson_order += 1
                    self.stdout.write(self.style.SUCCESS(f"OK — '{lesson.title}'"))

                except Exception as exc:
                    failed += 1
                    msg = f"ERREUR : {exc}"
                    logger.warning(
                        "generate_german_content: échec leçon %d niveau %s skill %s — %s",
                        lesson_order,
                        level,
                        skill,
                        exc,
                    )
                    if continue_on_error:
                        self.stdout.write(self.style.WARNING(msg))
                    else:
                        self.stderr.write(msg)
                        raise

                if sleep_sec > 0:
                    time.sleep(sleep_sec)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n  ✅ Niveau {level} terminé : {generated} leçon(s) créée(s), "
                f"{failed} échec(s)."
            )
        )
