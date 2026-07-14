from __future__ import annotations

import json
import logging
import re
import time

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from preparation_tests.models import Exam, ExamSection, CourseLesson, CourseExercise, Asset
from ai_engine.services.llm_service import call_llm
from ai_engine.services.tts_service import generate_audio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt système — expert pédagogique TCF Français
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
Tu es un expert pédagogique de premier plan spécialisé dans l'enseignement et l'évaluation du français langue étrangère (FLE).
Tu génères du contenu pédagogique de haute qualité pour la préparation au test officiel TCF (Test de Connaissance du Français), en particulier pour le TCF Canada ou TCF tout public.

Tu retournes UNIQUEMENT un objet JSON valide (sans texte avant ou après, sans balise markdown), avec la structure exacte suivante :

{
  "title": "Titre de la leçon de Compréhension Orale en français",
  "intro": "Courte introduction (2-3 phrases) en français expliquant les objectifs de la leçon de compréhension orale",
  "content": "Contenu pédagogique complet en HTML simple (<h3>, <p>, <ul>, <li>, <strong>, <em>) expliquant la méthodologie, le vocabulaire thématique et les pièges classiques pour cette thématique de compréhension orale.",
  "exercises": [
    {
      "audio_text": "Le texte oral (dialogue, annonce publique, message répondeur, conversation) en français qui sera lu par la synthèse vocale (TTS). Ce texte doit être réaliste, calibré pour le niveau requis, et d'une longueur appropriée.",
      "question_text": "La question posée sur ce document audio (en français).",
      "option_a": "Option A",
      "option_b": "Option B",
      "option_c": "Option C",
      "option_d": "Option D",
      "correct_option": "A",
      "explanation": "Explication de la bonne réponse en français, en expliquant pourquoi les autres options sont incorrectes ou des distracteurs."
    }
  ]
}

Règles impératives :
- Adapter rigoureusement au niveau CECR indiqué (du niveau A1 débutant très simple au niveau C2 très complexe).
- 4 options par exercice (A, B, C, D), une seule correcte. Option C et D doivent être remplies obligatoirement.
- correct_option = "A", "B", "C" ou "D" uniquement.
- Contenu HTML sans balises <html>, <head>, <body>.
- JSON strict, pas de commentaires, pas de texte autour.
"""

LEVEL_DESCRIPTIONS = {
    "A1": "débutant absolu — phrases très simples, annonces et messages très courts",
    "A2": "élémentaire — dialogues du quotidien, annonces de gares ou aéroports",
    "B1": "intermédiaire — discussions de travail courantes, reportages radio simples",
    "B2": "intermédiaire avancé — débats de société complexes, opinions nuancées",
    "C1": "avancé — conférences universitaires, argumentations abstraites, implicite fort",
    "C2": "maîtrise — débats spécialisés, nuances littéraires, idiomes et expressions idiomatiques complexes",
}

ALL_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def _extract_json(raw: str) -> dict:
    """Extrait et parse le JSON depuis la réponse LLM (robuste aux backticks)."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

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
        for f in ("audio_text", "question_text", "option_a", "option_b", "option_c", "option_d",
                  "correct_option", "explanation"):
            if f not in ex:
                raise ValueError(f"Exercice {i}: champ manquant '{f}'")
        if ex["correct_option"] not in ("A", "B", "C", "D"):
            raise ValueError(
                f"Exercice {i}: correct_option='{ex['correct_option']}' invalide."
            )


def _build_user_prompt(level: str, exercises_count: int, lesson_order: int) -> str:
    level_desc = LEVEL_DESCRIPTIONS.get(level, level)

    prompt = (
        f"Génère la leçon de Compréhension Orale TCF n°{lesson_order} pour le niveau {level} ({level_desc}).\n"
        f"Nombre d'exercices QCM à inclure : {exercises_count}.\n\n"
        "Règles strictes de calibrage CECR pour la compréhension orale (CO) du TCF :\n"
    )

    if level == "A1":
        prompt += (
            "- Situations : messages très courts de la vie quotidienne, salutations simples, prix, heures, indications de direction basiques.\n"
            "- Texte audio ('audio_text') : 1 ou 2 phrases très lentes, vocabulaire basique de survie.\n"
        )
    elif level == "A2":
        prompt += (
            "- Situations : messages sur répondeur téléphonique, annonces en gare ou aéroport simples, dialogues familiers très courts.\n"
            "- Texte audio ('audio_text') : 3 à 4 phrases claires avec connecteurs simples, débit modéré.\n"
        )
    elif level == "B1":
        prompt += (
            "- Situations : dialogues au travail, conversations courantes, instructions simples, reportages radio courts sur des sujets familiers.\n"
            "- Texte audio ('audio_text') : débit normal, structures avec subordonnées, idées principales explicites.\n"
        )
    elif level == "B2":
        prompt += (
            "- Situations : débats d'actualité, exposés courts, conférences, actualités radio complexes.\n"
            "- Texte audio ('audio_text') : débit naturel rapide, opinions nuancées, expressions idiomatiques courantes.\n"
        )
    elif level == "C1":
        prompt += (
            "- Situations : conférences académiques, interviews politiques ou philosophiques denses, reportages radio complexes.\n"
            "- Texte audio ('audio_text') : débit soutenu, argumentation complexe, implicite fort, connecteurs fins.\n"
        )
    elif level == "C2":
        prompt += (
            "- Situations : extraits de pièces littéraires lues, débats scientifiques de pointe, jeux de mots et ironie fine.\n"
            "- Texte audio ('audio_text') : structure hautement littéraire ou très rapide, expressions idiomatiques rares, nuances de ton et de registre.\n"
        )

    prompt += (
        "\nIMPORTANT : Le champ 'audio_text' de chaque exercice DOIT contenir uniquement le script du dialogue/annonce à lire "
        "en français pour la synthèse vocale, sans consignes ni traductions.\n"
    )

    return prompt


def _build_asset(rel_audio_path: str, language: str, title: str = "") -> Asset:
    """Création Asset robuste selon les champs réellement présents."""
    field_names = {f.name for f in Asset._meta.concrete_fields}
    kwargs = {}

    if "kind" in field_names:
        kwargs["kind"] = "audio"
    elif "type" in field_names:
        kwargs["type"] = "audio"

    if "lang" in field_names:
        kwargs["lang"] = language
    elif "locale" in field_names:
        kwargs["locale"] = language

    if "title" in field_names and title:
        kwargs["title"] = title

    asset = Asset.objects.create(**kwargs)

    if "file" in field_names:
        setattr(asset, "file", rel_audio_path)
        asset.save(update_fields=["file"])
    elif "path" in field_names:
        setattr(asset, "path", rel_audio_path)
        asset.save(update_fields=["path"])
    else:
        asset.save()

    return asset


class Command(BaseCommand):
    help = "Génère des leçons et exercices TCF français (CO) via LLM et TTS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Niveau CECR : A1, A2, B1, B2, C1, C2. Si absent, génère pour tous.",
        )
        parser.add_argument(
            "--lessons",
            type=int,
            default=5,
            help="Nombre de leçons à générer par niveau (défaut: 5)",
        )
        parser.add_argument(
            "--exercises",
            type=int,
            default=10,
            help="Nombre d'exercices par leçon (défaut: 10)",
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
        total_lessons = options["lessons"]
        exercises_count = options["exercises"]
        sleep_sec = options["sleep"]
        continue_on_error = options["continue_on_error"]

        # Créer ou récupérer l'examen TCF
        tcf_exam, created_exam = Exam.objects.get_or_create(
            code="tcf",
            defaults={
                "name": "TCF Canada",
                "language": "fr",
                "description": "Test de Connaissance du Français pour l'immigration et les études."
            }
        )

        levels = [level_arg.upper()] if level_arg else ALL_LEVELS

        for level in levels:
            if level not in ALL_LEVELS:
                self.stderr.write(f"Niveau inconnu : '{level}'. Ignoré.")
                continue

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"\n▶ Génération TCF niveau {level} ({total_lessons} leçons, {exercises_count} exos/leçon)"
                )
            )

            # Ordre de départ
            existing_count = CourseLesson.objects.filter(exams=tcf_exam, section="co", level=level).count()
            lesson_order = existing_count + 1

            generated = 0
            failed = 0

            for i in range(1, total_lessons + 1):
                self.stdout.write(
                    f"    [{lesson_order}] Génération leçon {i}/{total_lessons}…", ending=" "
                )
                self.stdout.flush()

                user_prompt = _build_user_prompt(
                    level=level,
                    exercises_count=exercises_count,
                    lesson_order=lesson_order,
                )

                try:
                    # Appel direct Gemini avec garantie JSON
                    client, err = get_vertex_client()
                    if err or not client:
                        raise RuntimeError(f"Vertex AI Client init error: {err}")
                    
                    from google.genai import types
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.5,
                            response_mime_type="application/json"
                        )
                    )
                    raw = response.text
                    data = _extract_json(raw)
                    _validate_lesson(data, exercises_count)

                    # Création de la leçon
                    lesson = CourseLesson.objects.create(
                        title=data["title"][:255],
                        slug=slugify(f"tcf-co-{level}-{lesson_order}").lower(),
                        section="co",
                        level=level,
                        content_html=data["content"],
                        order=lesson_order,
                        is_published=True,
                    )
                    lesson.exams.add(tcf_exam)

                    exo_list = data["exercises"][:exercises_count]
                    for idx, exo_data in enumerate(exo_list):
                        # Génération audio TTS en français
                        audio_text = exo_data["audio_text"]
                        
                        try:
                            rel_audio = generate_audio(audio_text, language="fr", output_dir="assets")
                            asset = _build_asset(rel_audio, language="fr", title=f"Audio TCF CO {level} L{lesson_order} Ex{idx+1}")
                        except Exception as tts_err:
                            self.stdout.write(self.style.WARNING(f"TTS Fail: {tts_err}"))
                            asset = None

                        CourseExercise.objects.create(
                            lesson=lesson,
                            title=f"Question {idx+1}",
                            instruction="Écoutez le document sonore et répondez à la question.",
                            question_text=exo_data["question_text"],
                            audio=asset,
                            option_a=exo_data["option_a"][:255],
                            option_b=exo_data["option_b"][:255],
                            option_c=exo_data["option_c"][:255],
                            option_d=exo_data["option_d"][:255],
                            correct_option=exo_data["correct_option"],
                            summary=exo_data.get("explanation", ""),
                            order=idx + 1,
                            is_active=True,
                        )

                    generated += 1
                    lesson_order += 1
                    self.stdout.write(self.style.SUCCESS(f"OK — '{lesson.title}'"))

                except Exception as exc:
                    failed += 1
                    msg = f"ERREUR : {exc}"
                    logger.warning(
                        "generate_tcf_content: échec leçon %d niveau %s — %s",
                        lesson_order,
                        level,
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
                    f"\n  Niveau {level} terminé : {generated} leçon(s) créée(s), {failed} échec(s)."
                )
            )
