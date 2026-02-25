"""
Service d'insertion CO - PRODUCTION SAFE
Aligné sur les modèles réels:
- Asset: id, kind, file, lang, created_at
- CourseLesson: exam, exams, section, level, title, slug, locale, content_html, order, is_published
- CourseExercise: lesson, title, instruction, question_text, audio, image, option_a/b/c/d, correct_option, summary, order, is_active
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from django.utils.text import slugify


def _create_audio_asset(audio_path: str, language: str = "fr") -> Any:
    """
    Crée un Asset audio selon le schéma réel:
    Asset(kind, file, lang)
    """
    from preparation_tests.models import Asset

    asset = Asset.objects.create(
        kind="audio",
        file=audio_path,
        lang=language,
    )
    return asset


def _normalize_questions(co_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrait et normalise les questions depuis co_data.
    Gère plusieurs formats possibles de l'agent IA.
    """
    questions = co_data.get("questions", [])
    if not questions:
        questions = co_data.get("exercises", [])
    if not questions:
        questions = co_data.get("items", [])

    normalized = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        # Extraction question_text
        question_text = (
            q.get("question_text")
            or q.get("question")
            or q.get("stem")
            or q.get("text")
            or ""
        )

        # Extraction instruction
        instruction = (
            q.get("instruction")
            or q.get("instructions")
            or q.get("prompt")
            or ""
        )

        # Extraction options (plusieurs formats possibles)
        options = q.get("options", [])
        choices = q.get("choices", [])

        if choices and not options:
            # Format: choices = [{"text": "...", "is_correct": True}, ...]
            options = [c.get("text", "") if isinstance(c, dict) else str(c) for c in choices]

        # Remplissage options A/B/C/D
        option_a = options[0] if len(options) > 0 else q.get("option_a", "")
        option_b = options[1] if len(options) > 1 else q.get("option_b", "")
        option_c = options[2] if len(options) > 2 else q.get("option_c", "")
        option_d = options[3] if len(options) > 3 else q.get("option_d", "")

        # Extraction correct_option
        correct = q.get("correct_option", q.get("correct_answer", q.get("correct", "")))
        if isinstance(correct, int):
            correct = ["A", "B", "C", "D"][correct] if 0 <= correct < 4 else "A"
        elif isinstance(correct, str):
            correct = correct.upper().strip()
            if correct not in ("A", "B", "C", "D"):
                # Chercher par texte
                if choices:
                    for idx, c in enumerate(choices):
                        if isinstance(c, dict) and c.get("is_correct"):
                            correct = ["A", "B", "C", "D"][idx] if idx < 4 else "A"
                            break
                    else:
                        correct = "A"
                else:
                    correct = "A"

        # Titre
        title = q.get("title", f"Exercice {i + 1}")

        # Summary
        summary = q.get("summary", q.get("explanation", ""))

        normalized.append({
            "title": title,
            "instruction": instruction,
            "question_text": question_text,
            "option_a": option_a,
            "option_b": option_b,
            "option_c": option_c,
            "option_d": option_d,
            "correct_option": correct,
            "summary": summary,
            "order": i + 1,
        })

    return normalized


def insert_co_content(
    exam_id: int,
    level: str,
    language: str,
    co_data: Dict[str, Any],
    audio_path: Optional[str] = None,
) -> Any:
    """
    Insère une leçon CO complète avec ses exercices.

    Args:
        exam_id: ID de l'examen (Exam.id)
        level: Niveau CECR (A1, A2, B1, B2, C1, C2)
        language: Langue/locale (fr, en, de)
        co_data: Contenu généré par l'agent IA
        audio_path: Chemin relatif de l'audio (optionnel)

    Returns:
        CourseLesson créée
    """
    from preparation_tests.models import Asset, CourseExercise, CourseLesson, Exam

    # Validation exam
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        raise ValueError(f"Exam with id={exam_id} not found")

    # Extraction données leçon
    title = co_data.get("title", f"CO {level} - Leçon")
    content_html = co_data.get("content_html", co_data.get("audio_script", ""))

    # Génération slug unique
    base_slug = slugify(f"{level}-co-{title[:30]}")
    slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

    # Calcul order
    existing_count = CourseLesson.objects.filter(
        section="co",
        level=level.upper(),
    ).count()
    order = existing_count + 1

    # Création leçon
    lesson = CourseLesson.objects.create(
        exam=exam,  # Legacy FK
        section="co",
        level=level.upper(),
        title=title,
        slug=slug,
        locale=language,
        content_html=content_html,
        order=order,
        is_published=True,
    )

    # Lien M2M exams
    lesson.exams.add(exam)

    # Création Asset audio si fourni
    audio_asset = None
    if audio_path:
        audio_asset = _create_audio_asset(audio_path, language)

    # Normalisation et création exercices
    questions = _normalize_questions(co_data)

    for q in questions:
        CourseExercise.objects.create(
            lesson=lesson,
            title=q["title"],
            instruction=q["instruction"],
            question_text=q["question_text"],
            audio=audio_asset,  # Même audio pour tous les exercices de la leçon
            image=None,
            option_a=q["option_a"],
            option_b=q["option_b"],
            option_c=q["option_c"],
            option_d=q["option_d"],
            correct_option=q["correct_option"],
            summary=q["summary"],
            order=q["order"],
            is_active=True,
        )

    return lesson