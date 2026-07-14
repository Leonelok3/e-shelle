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
  "title": "Titre de la leçon en français",
  "intro": "Courte introduction (2-3 phrases) en français expliquant les objectifs de la leçon",
  "content": "Contenu pédagogique complet en HTML simple (<h3>, <p>, <ul>, <li>, <strong>, <em>) expliquant la méthodologie, le vocabulaire thématique, les structures grammaticales clés et les pièges classiques.",
  "exercises": [
    {
      "audio_text": "Le texte oral pour la CO, OU le court texte/document à lire pour la CE, OU le contexte/sujet court pour la EE/EO.",
      "question_text": "La question posée (pour CO/CE) OU le sujet/consigne de rédaction/prise de parole (pour EE/EO).",
      "option_a": "Option A (laisser vide pour EE/EO)",
      "option_b": "Option B (laisser vide pour EE/EO)",
      "option_c": "Option C (laisser vide pour EE/EO)",
      "option_d": "Option D (laisser vide pour EE/EO)",
      "correct_option": "A (toujours laisser à A pour EE/EO)",
      "explanation": "Explication de la bonne réponse (pour CO/CE) OU grille d'évaluation, attentes et suggestions de points à aborder (pour EE/EO)."
    }
  ]
}

Règles impératives :
- Adapter rigoureusement au niveau CECR indiqué (du niveau A1 débutant très simple au niveau C2 très complexe).
- Pour CO/CE : les 4 options (A, B, C, D) et correct_option ("A", "B", "C" ou "D") sont obligatoires.
- Pour EE/EO : les options (option_a, option_b, option_c, option_d) doivent être des chaînes vides (""). correct_option doit impérativement être la lettre "A".
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


def _build_user_prompt(level: str, section: str, exercises_count: int, lesson_order: int) -> str:
    level_desc = LEVEL_DESCRIPTIONS.get(level, level)
    
    if section == "co":
        section_label = "Compréhension Orale"
    elif section == "ce":
        section_label = "Compréhension Écrite"
    elif section == "ee":
        section_label = "Expression Écrite"
    else:
        section_label = "Expression Orale"

    prompt = (
        f"Génère la leçon de {section_label} TCF n°{lesson_order} pour le niveau {level} ({level_desc}).\n"
        f"Nombre d'exercices à inclure : {exercises_count}.\n\n"
    )

    if section == "co":
        prompt += "Règles strictes de calibrage CECR pour la compréhension orale (CO) du TCF :\n"
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
    elif section == "ce":
        prompt += "Règles strictes de calibrage CECR pour la compréhension écrite (CE) du TCF :\n"
        if level == "A1":
            prompt += (
                "- Type de document : panneaux publics simples, courts messages amicaux (SMS), étiquettes de prix, formulaires très basiques.\n"
                "- Difficulté : vocabulaire de base du quotidien immédiat, phrases extrêmement courtes.\n"
            )
        elif level == "A2":
            prompt += (
                "- Type de document : petites annonces, menus de restaurant, horaires de transports, e-mails amicaux simples de quelques lignes.\n"
                "- Difficulté : connecteurs logiques de base, temps du présent et passé composé.\n"
            )
        elif level == "B1":
            prompt += (
                "- Type de document : articles de journaux d'actualité simple, courriels professionnels informatifs, prospectus touristiques.\n"
                "- Difficulté : vocabulaire standard élargi, structures de phrases complexes (subordonnées relâchées).\n"
            )
        elif level == "B2":
            prompt += (
                "- Type de document : articles d'opinion, éditoriaux de presse, rapports techniques généraux sur des thèmes d'actualité.\n"
                "- Difficulté : argumentation articulée, points de vue implicites, expressions courantes nuancées.\n"
            )
        elif level == "C1":
            prompt += (
                "- Type de document : extraits de textes littéraires modernes, articles scientifiques vulgarisés, correspondances administratives denses.\n"
                "- Difficulté : style soutenu, vocabulaire abstrait étendu, structures syntaxiques complexes.\n"
            )
        elif level == "C2":
            prompt += (
                "- Type de document : textes littéraires classiques, articles de recherche hautement spécialisés, textes juridiques ou réglementaires denses.\n"
                "- Difficulté : vocabulaire très rare ou archaïque, figures de style complexes, nuances de registre extrêmes.\n"
            )

        prompt += (
            "\nStructure obligatoire du HTML dans 'content' (Leçon de Lecture) :\n"
            "1. <h3>1. Introduction</h3> : Présentation du thème en français.\n"
            "2. <h3>2. Vocabulaire essentiel</h3> : Liste de mots clés en français (strong) avec leur définition courte entre parenthèses.\n"
            "3. <h3>3. Documents de lecture</h3> : Les documents ou courts textes en français à lire (placés dans des blocs '<div class=\"reading-box\">...</div>'). Aucun mot anglais ou de traduction dans ces textes.\n"
            "4. <h3>4. Conseils pour l'épreuve</h3> : Stratégies de lecture rapide et d'élimination de distracteurs.\n\n"
            "IMPORTANT : Le champ 'audio_text' de chaque exercice doit simplement contenir le court extrait de texte spécifique (issu des Documents de lecture) sur lequel porte la question.\n"
        )
    elif section == "ee":
        prompt += "Règles strictes de calibrage CECR pour l'expression écrite (EE) du TCF :\n"
        if level == "A1":
            prompt += (
                "- Sujets : écrire un message amical très simple, décrire un objet de tous les jours, donner des informations personnelles basiques.\n"
                "- Longueur : 40 à 60 mots.\n"
            )
        elif level == "A2":
            prompt += (
                "- Sujets : inviter quelqu'hui, s'excuser dans un court message, raconter une journée simple au passé.\n"
                "- Longueur : 60 à 80 mots.\n"
            )
        elif level == "B1":
            prompt += (
                "- Sujets : rédiger une lettre personnelle décrivant un projet, un courriel formel de demande d'information simple.\n"
                "- Longueur : 80 à 120 mots.\n"
            )
        elif level == "B2":
            prompt += (
                "- Sujets : lettre formelle de réclamation, texte argumentatif structuré défendant un point de vue sur un sujet de société.\n"
                "- Longueur : 120 à 180 mots.\n"
            )
        elif level == "C1":
            prompt += (
                "- Sujets : synthèse de documents contradictoires, essai argumentatif complexe sur un thème abstrait.\n"
                "- Longueur : 180 à 250 mots.\n"
            )
        elif level == "C2":
            prompt += (
                "- Sujets : critique d'une œuvre littéraire ou scientifique, tribune d'opinion extrêmement raffinée avec figures de style.\n"
                "- Longueur : 250 mots ou plus.\n"
            )

        prompt += (
            "\nStructure obligatoire du HTML dans 'content' (Leçon d'Écriture) :\n"
            "1. <h3>1. Introduction</h3> : Présentation des objectifs de rédaction.\n"
            "2. <h3>2. Vocabulaire et Connecteurs</h3> : Liste d'expressions et connecteurs logiques de transition en français (strong).\n"
            "3. <h3>3. Modèles de rédaction</h3> : Exemples de textes rédigés avec annotations structurelles.\n"
            "4. <h3>4. Stratégie et Méthode</h3> : Astuces pour structurer le texte et éviter les fautes d'accord.\n\n"
            "IMPORTANT : Chaque exercice de 'exercises' doit proposer un sujet de rédaction complet.\n"
            "- option_a, option_b, option_c, option_d doivent être des chaînes vides (\"\").\n"
            "- correct_option doit être défini à \"A\".\n"
            "- explanation doit contenir une grille d'évaluation indicative et des points à respecter.\n"
        )
    elif section == "eo":
        prompt += "Règles strictes de calibrage CECR pour l'expression orale (EO) du TCF :\n"
        if level == "A1":
            prompt += (
                "- Sujets : se présenter simplement, épeler son nom, donner son numéro de téléphone ou parler de ses goûts immédiats.\n"
                "- Durée recommandée : 1 à 1.5 minute.\n"
            )
        elif level == "A2":
            prompt += (
                "- Sujets : décrire son lieu de vie, présenter ses loisirs favoris, raconter un voyage passé simple.\n"
                "- Durée recommandée : 1.5 à 2 minutes.\n"
            )
        elif level == "B1":
            prompt += (
                "- Sujets : donner son avis sur un sujet du quotidien (travail, transports), justifier un choix personnel ou professionnel.\n"
                "- Durée recommandée : 2 à 3 minutes.\n"
            )
        elif level == "B2":
            prompt += (
                "- Sujets : débattre avec l'examinateur sur un thème d'actualité, poser des questions et argumenter.\n"
                "- Durée recommandée : 3 à 4 minutes.\n"
            )
        elif level == "C1":
            prompt += (
                "- Sujets : monologue soutenu sur un problème abstrait ou de société, réponse structurée à une contradiction de l'examinateur.\n"
                "- Durée recommandée : 4 à 5 minutes.\n"
            )
        elif level == "C2":
            prompt += (
                "- Sujets : débat d'experts, discours de persuasion raffiné utilisant l'ironie ou des métaphores sur des thèmes philosophiques.\n"
                "- Durée recommandée : 5 minutes ou plus.\n"
            )

        prompt += (
            "\nStructure obligatoire du HTML dans 'content' (Leçon d'Oral) :\n"
            "1. <h3>1. Introduction</h3> : Présentation des objectifs de prise de parole.\n"
            "2. <h3>2. Vocabulaire et Expressions clés</h3> : Formules pour structurer son discours, exprimer son accord/désaccord, nuancer.\n"
            "3. <h3>3. Exemples transcrits</h3> : Modèles de réponses orales transcrites avec commentaires pédagogiques.\n"
            "4. <h3>4. Conseils de communication</h3> : Gestion du débit, de l'intonation, et de l'interaction avec l'examinateur.\n\n"
            "IMPORTANT : Chaque exercice de 'exercises' doit proposer un sujet d'expression orale individuel.\n"
            "- option_a, option_b, option_c, option_d doivent être des chaînes vides (\"\").\n"
            "- correct_option doit être défini à \"A\".\n"
            "- explanation doit contenir des suggestions de points à aborder et des structures de phrases recommandées.\n"
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
            "--section",
            type=str,
            default="co",
            choices=["co", "ce", "ee", "eo"],
            help="Section à générer : co (Compréhension Orale), ce (Compréhension Écrite), ee (Expression Écrite), eo (Expression Orale)",
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
        section = (options["section"] or "co").lower()
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

            # Cible dynamique : 10 leçons pour C1/C2 et 5 pour les autres par défaut (sauf si --lessons a été explicitement spécifié)
            level_target = total_lessons if total_lessons != 5 else (10 if level in ("C1", "C2") else 5)

            existing_count = CourseLesson.objects.filter(exams=tcf_exam, section=section, level=level).count()
            needed = level_target - existing_count
            if needed <= 0:
                self.stdout.write(self.style.SUCCESS(f"▶ Niveau {level} ({section.upper()}) : déjà {existing_count}/{level_target} leçons. Passage au niveau suivant."))
                continue

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"\n▶ Génération TCF {section.upper()} niveau {level} ({needed} leçons nécessaires, {exercises_count} exos/leçon)"
                )
            )

            # Ordre de départ
            lesson_order = existing_count + 1

            generated = 0
            failed = 0

            for i in range(1, needed + 1):
                self.stdout.write(
                    f"    [{lesson_order}] Génération leçon {i}/{needed}…", ending=" "
                )
                self.stdout.flush()

                user_prompt = _build_user_prompt(
                    level=level,
                    section=section,
                    exercises_count=exercises_count,
                    lesson_order=lesson_order,
                )

                try:
                    # Appel direct Gemini avec garantie JSON
                    from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
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
                    base_slug = slugify(f"tcf-{section}-{level}-{lesson_order}").lower()
                    slug = base_slug
                    counter = 1
                    while CourseLesson.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1

                    lesson = CourseLesson.objects.create(
                        title=data["title"][:255],
                        slug=slug,
                        section=section,
                        level=level,
                        content_html=data["content"],
                        order=lesson_order,
                        is_published=True,
                    )
                    lesson.exams.add(tcf_exam)

                    exo_list = data["exercises"][:exercises_count]
                    for idx, exo_data in enumerate(exo_list):
                        asset = None
                        if section == "co":
                            # Génération audio TTS en français
                            audio_text = exo_data["audio_text"]
                            try:
                                rel_audio = generate_audio(audio_text, language="fr", output_dir="assets")
                                asset = _build_asset(rel_audio, language="fr", title=f"Audio TCF CO {level} L{lesson_order} Ex{idx+1}")
                            except Exception as tts_err:
                                self.stdout.write(self.style.WARNING(f"TTS Fail: {tts_err}"))
                                asset = None

                        instruction = (
                            "Écoutez le document sonore et répondez à la question."
                            if section == "co"
                            else "Lisez le document et répondez à la question."
                        )

                        CourseExercise.objects.create(
                            lesson=lesson,
                            title=f"Question {idx+1}",
                            instruction=instruction,
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
