from __future__ import annotations

import unicodedata
import json
import json
from django.shortcuts import get_object_or_404, render
from .models import CourseLesson, CourseExercise

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Exam,
    ExamSection,
    Question,
    Choice,
    Session,
    Attempt,
    Answer,
    CourseLesson,
    CourseExercise,
)

from .ai_coach import AICoachCO


# =========================================================
# 🔧 UTILITAIRES GÉNÉRAUX
# =========================================================

def _norm(s: str | None) -> str:
    """Normalise une chaîne (minuscule + sans accents)."""
    if not s:
        return ""
    s = s.strip().lower()
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _next_unanswered_question(attempt: Attempt) -> Question | None:
    """Retourne la prochaine question non répondue pour une tentative donnée."""
    answered_ids = set(
        attempt.answers.values_list("question_id", flat=True)
    )
    return (
        attempt.section.questions.exclude(id__in=answered_ids)
        .order_by("id")
        .first()
    )


def _audio_url_from_question(q: Question) -> str | None:
    """Retourne l'URL audio si la question a un asset audio."""
    try:
        if q.asset and q.asset.kind == "audio" and q.asset.url:
            return q.asset.url
    except Exception:
        pass
    return getattr(q, "audio_url", None)


# =========================================================
# 🏠 NAVIGATION GÉNÉRALE
# =========================================================

def home(request: HttpRequest) -> HttpResponse:
    """Page d'accueil avec redirection vers les modules d'examen."""
    return render(request, "preparation_tests/home.html")


# =========================================================
# 📝 EXAMENS DISPONIBLES
# =========================================================

def exam_list(request: HttpRequest) -> HttpResponse:
    """Liste de tous les examens disponibles."""
    exams = Exam.objects.all().order_by("language", "name")
    return render(
        request, "preparation_tests/exam_list.html", {"exams": exams}
    )


def exam_detail(request: HttpRequest, exam_code: str) -> HttpResponse:
    """Détail d'un examen spécifique avec ses sections."""
    exam = get_object_or_404(Exam, code=exam_code)
    sections = exam.sections.all()
    return render(
        request,
        "preparation_tests/exam_detail.html",
        {"exam": exam, "sections": sections},
    )


# =========================================================
# 🚀 DÉMARRAGE DE SESSION GÉNÉRIQUE (BANQUE DE QUESTIONS)
# =========================================================

@login_required
def start_session_generic(
    request: HttpRequest, exam_code: str
) -> HttpResponse:
    """
    Démarre une session pour un examen donné avec section choisie
    en utilisant le moteur générique (ExamSection + Question).
    """
    exam = get_object_or_404(Exam, code=exam_code)

    wanted = _norm(request.GET.get("section", ""))  # ex. 'co'
    aliases = {
        "co": {"co", "comprehension orale", "compréhension orale", "listening"},
        "ce": {"ce", "comprehension ecrite", "compréhension écrite", "reading"},
        "ee": {"ee", "expression ecrite", "expression écrite", "writing"},
        "eo": {"eo", "expression orale", "speaking"},
    }

    section = None
    if wanted:
        # tentative directe
        section = exam.sections.filter(code__iexact=wanted).first()

    if not section and wanted:
        for sec in exam.sections.all():
            sec_norm = _norm(sec.code)
            for short, bag in aliases.items():
                if wanted in bag and sec_norm in bag:
                    section = sec
                    break
            if section:
                break

    section = section or exam.sections.order_by("order").first()
    if not section:
        messages.error(request, "Aucune section définie pour cet examen.")
        return redirect(
            "preparation_tests:exam_detail", exam_code=exam.code
        )

    session = Session.objects.create(
        user=request.user, exam=exam, mode="practice"
    )
    attempt = Attempt.objects.create(session=session, section=section)

    return redirect(
        "preparation_tests:take_section", attempt_id=attempt.id
    )


# =========================================================
# 🧩 PASSATION DES QUESTIONS (MOTEUR GÉNÉRIQUE)
# =========================================================
@login_required
def take_section(request: HttpRequest, attempt_id: int) -> HttpResponse:
    """Affiche la prochaine question ou le résultat si terminé."""
    attempt = get_object_or_404(
        Attempt, id=attempt_id, session__user=request.user
    )
    section = attempt.section
    exam = section.exam  # <<< on récupère l'examen
    q = _next_unanswered_question(attempt)

    # Fin de section ?
    if not q:
        total = section.questions.count()
        correct = attempt.answers.filter(is_correct=True).count()
        attempt.total_items = total
        attempt.raw_score = float(correct)
        attempt.ended_at = timezone.now()
        attempt.save(
            update_fields=["total_items", "raw_score", "ended_at"]
        )
        attempt.session.completed_at = timezone.now()
        attempt.session.save(update_fields=["completed_at"])
        return redirect(
            "preparation_tests:session_result",
            session_id=attempt.session.id,
        )

    # Progression
    answered_count = attempt.answers.count()
    total_questions = section.questions.count()
    current_index = answered_count + 1

    # Question suivante
    audio_url = _audio_url_from_question(q)
    choices = q.choices.all() if q.subtype == "mcq" else None

    return render(
        request,
        "preparation_tests/question.html",
        {
            "attempt": attempt,
            "section": section,
            "exam": exam,  # <<< important pour tef_course_base.html
            "question": q,
            "choices": choices,
            "duration_sec": section.duration_sec,
            "audio_url": audio_url,
            "current_index": current_index,
            "total_questions": total_questions,
        },
    )

# =========================================================
# ✅ SOUMISSION DE RÉPONSE (MOTEUR GÉNÉRIQUE)
# =========================================================

@login_required
def submit_answer(
    request: HttpRequest, attempt_id: int, question_id: int
) -> HttpResponse:
    """Soumet la réponse d'une question."""
    if request.method != "POST":
        raise Http404()

    attempt = get_object_or_404(
        Attempt, id=attempt_id, session__user=request.user
    )
    question = get_object_or_404(
        Question, id=question_id, section=attempt.section
    )
    payload, is_correct = {}, False

    if question.subtype == "mcq":
        choice_id = request.POST.get("choice")
        if not choice_id:
            messages.error(request, "Veuillez sélectionner une réponse.")
            return redirect(
                "preparation_tests:take_section", attempt_id=attempt.id
            )
        try:
            choice = Choice.objects.get(id=int(choice_id), question=question)
            is_correct = choice.is_correct
            payload = {"choice_id": choice.id}
        except Choice.DoesNotExist:
            messages.error(request, "Choix invalide.")
            return redirect(
                "preparation_tests:take_section", attempt_id=attempt.id
            )
    else:
        text = (request.POST.get("text") or "").strip()
        if not text:
            messages.error(request, "Veuillez saisir une réponse.")
            return redirect(
                "preparation_tests:take_section", attempt_id=attempt.id
            )
        payload = {"text": text}

    Answer.objects.create(
        attempt=attempt, question=question, payload=payload, is_correct=is_correct
    )
    return redirect(
        "preparation_tests:take_section", attempt_id=attempt.id
    )


# =========================================================
# 📊 AFFICHAGE DES RÉSULTATS (+ COACH IA TEF CO)
# =========================================================

# =========================================================
# 📊 AFFICHAGE DES RÉSULTATS
# =========================================================

@login_required
def session_result(request: HttpRequest, session_id: int) -> HttpResponse:
    """Affiche les résultats d'une session complète."""
    session = get_object_or_404(Session, id=session_id, user=request.user)
    attempts = session.attempts.select_related("section").all()

    total_items = sum(a.total_items for a in attempts)
    total_correct = sum(int(a.raw_score) for a in attempts)

    # Pourcentage global (0–100)
    if total_items > 0:
        global_pct = int(round((total_correct / total_items) * 100))
    else:
        global_pct = 0

    # --- Analyse IA CO uniquement pour le TEF CO ---
    analysis = None
    if session.exam.code.lower() == "tef":
        # on cherche d'abord une section "co", sinon "listening"
        co_attempt = (
            attempts.filter(section__code__iexact="co").first()
            or attempts.filter(section__code__iexact="listening").first()
        )
        if co_attempt:
            analysis = AICoachCO.analyze_attempt(co_attempt)

    return render(
        request,
        "preparation_tests/result.html",
        {
            "session": session,
            "attempts": attempts,
            "total_items": total_items,
            "total_correct": total_correct,
            "global_pct": global_pct,    # ✅ nouveau
            "analysis": analysis,
        },
    )

    
# =========================================================
# 🌍 HUBS DE LANGUES ET EXAMENS
# =========================================================

def french_exams(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/french_exams.html")


def tef_hub(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/fr_tef_hub.html")


def tcf_hub(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/fr_tcf_hub.html")


def delf_hub(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/fr_delf_hub.html")


def english_exams(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/english_exams.html")


def german_exams(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/german_exams.html")


# =========================================================
# 📚 COURS TEF (LEÇONS + EXERCICES)
# =========================================================

def tef_co(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef", section="co", is_published=True, locale="fr"
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request, "preparation_tests/tef_co.html", {"lessons": lessons}
    )


def tef_ce(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef", section="ce", is_published=True, locale="fr"
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request, "preparation_tests/tef_ce.html", {"lessons": lessons}
    )


def tef_ee(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef", section="ee", is_published=True, locale="fr"
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request, "preparation_tests/tef_ee.html", {"lessons": lessons}
    )


def tef_eo(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef", section="eo", is_published=True, locale="fr"
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request, "preparation_tests/tef_eo.html", {"lessons": lessons}
    )


# =========================================================
# 🎯 WRAPPER PRATIQUE (MOTEUR GÉNÉRIQUE)
# =========================================================

def start_session_with_section(
    request: HttpRequest, exam_code: str, section_code: str
) -> HttpResponse:
    """Redirige vers start_session_generic en injectant la section."""
    q = request.GET.copy()
    q["section"] = section_code
    request.GET = q
    return start_session_generic(request, exam_code)


# =========================================================
# 🟢 START_SESSION UTILISÉ PAR LE BOUTON "COMMENCER UNE SESSION"
#     → MODE ENTRAÎNEMENT (practice)
# =========================================================

@login_required
def start_session(request: HttpRequest, exam_code: str) -> HttpResponse:
    """
    Si on clique sur "Commencer une session CO" pour le TEF :
    → on envoie l'utilisateur directement sur la session de la 1ère leçon CO.
    Pour les autres cas : on utilise le moteur générique.
    """
    section_param = (request.GET.get("section") or "").lower()

    # Cas TEF + CO : rediriger vers la première leçon CO
    if exam_code.lower() == "tef" and (section_param in ("co", "") or not section_param):
        first_lesson = (
            CourseLesson.objects.filter(
                exam__code="tef",
                section="co",
                is_published=True,
                locale="fr",
            )
            .order_by("order", "id")
            .first()
        )
        if first_lesson:
            return redirect(
                "preparation_tests:lesson_session_co",
                lesson_id=first_lesson.id,
            )
        # Si aucune leçon : on renvoie simplement vers la page des cours CO
        return redirect("preparation_tests:tef_co")

    # Pour tout le reste : moteur générique (mode entraînement)
    return start_session_generic(request, exam_code)


# =========================================================
# 🧠 SESSION CO PAR LEÇON (COURSELESSON + COURSEEXERCISE)
#     → MODE ENTRAÎNEMENT COURS
# =========================================================

def lesson_session_co(
    request: HttpRequest, lesson_id: int
) -> HttpResponse:
    """
    Lance une session d'exercices CO pour UNE leçon donnée.
    Utilise CourseLesson + CourseExercise et le template tef_session_co.html.
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="co",
        is_published=True,
    )

    exercises_qs = CourseExercise.objects.filter(
        lesson=lesson, is_active=True
    ).order_by("order", "id")

    exercises: list[dict] = []
    for ex in exercises_qs:
        options: dict[str, str] = {}
        if ex.option_a:
            options["A"] = ex.option_a
        if ex.option_b:
            options["B"] = ex.option_b
        if ex.option_c:
            options["C"] = ex.option_c
        if ex.option_d:
            options["D"] = ex.option_d

        exercises.append(
            {
                "audio_url": ex.audio.url if ex.audio else "",
                "instruction": ex.instruction or "",
                "question": ex.question_text,
                "options": options,
                "correct": ex.correct_option or "",
                "explanation": ex.summary or "",
            }
        )

    exercises_json = json.dumps(exercises, ensure_ascii=False)

    return render(
        request,
        "preparation_tests/tef_session_co.html",
        {
            "lesson": lesson,
            "exercises_json": exercises_json,
            "total_exercises": len(exercises),
        },
    )


# =========================================================
# 🧪 MODE EXAMEN BLANC – TEF COMPRÉHENSION ORALE
# =========================================================

@login_required
def start_mock_tef_co(request: HttpRequest) -> HttpResponse:
    """
    Lance un EXAMEN BLANC TEF – Compréhension Orale.

    - Crée une Session en mode 'mock'
    - Crée une Attempt sur la section 'listening' du TEF
    - Réutilise le même moteur de questions (take_section + submit_answer)
    """
    exam = get_object_or_404(Exam, code="tef")

    # On récupère la section d'examen "listening" (CO officielle)
    section = exam.sections.filter(
        code=ExamSection.SectionCode.LISTENING
    ).first()

    if not section:
        messages.error(
            request,
            "La section de Compréhension Orale du TEF n'est pas encore configurée.",
        )
        return redirect("preparation_tests:exam_detail", exam_code="tef")

    # Session en mode EXAMEN BLANC
    session = Session.objects.create(
        user=request.user,
        exam=exam,
        mode="mock",  # cohérent avec MODE_CHOICES du modèle Session
    )
    attempt = Attempt.objects.create(session=session, section=section)

    # On réutilise le flux générique
    return redirect("preparation_tests:take_section", attempt_id=attempt.id)


## partie CE

def lesson_session_ce(request, lesson_id: int):
    """
    Session d'exercices CE pour UNE leçon donnée (comme CO, mais pour la lecture).
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="ce",
        is_published=True,
    )

    exercises_qs = CourseExercise.objects.filter(
        lesson=lesson,
        is_active=True
    ).order_by("order", "id")

    exercises: list[dict] = []
    for ex in exercises_qs:
        options: dict[str, str] = {}
        if ex.option_a:
            options["A"] = ex.option_a
        if ex.option_b:
            options["B"] = ex.option_b
        if ex.option_c:
            options["C"] = ex.option_c
        if ex.option_d:
            options["D"] = ex.option_d

        exercises.append(
            {
                # texte de consigne / introduction (facultatif)
                "instruction": ex.instruction or "Lis le texte puis choisis la bonne réponse.",
                # ici tu mets ton texte d’énoncé CE si tu as un champ dédié
                # adapte le nom du champ si besoin (ex. ex.text, ex.source_text, etc.)
                "text": getattr(ex, "text", "") or "",
                "question": ex.question_text,
                "options": options,
                "correct": ex.correct_option or "",
                "explanation": ex.summary or "",
            }
        )

    exercises_json = json.dumps(exercises, ensure_ascii=False)

    return render(
        request,
        "preparation_tests/tef_session_ce.html",
        {
            "lesson": lesson,
            "exercises_json": exercises_json,
            "total_exercises": len(exercises),
        },
    )


# =========================================================
# 🧠 SESSION CE PAR LEÇON (COURSELESSON + COURSEEXERCISE)
#     → MODE ENTRAÎNEMENT COURS (LECTURE)
# =========================================================

def lesson_session_ce(
    request: HttpRequest, lesson_id: int
) -> HttpResponse:
    """
    Lance une session d'exercices CE pour UNE leçon donnée.
    Utilise CourseLesson + CourseExercise et le template tef_session_ce.html.
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="ce",
        is_published=True,
    )

    exercises_qs = CourseExercise.objects.filter(
        lesson=lesson, is_active=True
    ).order_by("order", "id")

    exercises: list[dict] = []
    for ex in exercises_qs:
        options: dict[str, str] = {}
        if ex.option_a:
            options["A"] = ex.option_a
        if ex.option_b:
            options["B"] = ex.option_b
        if ex.option_c:
            options["C"] = ex.option_c
        if ex.option_d:
            options["D"] = ex.option_d

        exercises.append(
            {
                "instruction": ex.instruction or "",
                "question": ex.question_text,
                "options": options,
                "correct": ex.correct_option or "",
                "explanation": ex.summary or "",
            }
        )

    exercises_json = json.dumps(exercises, ensure_ascii=False)

    return render(
        request,
        "preparation_tests/tef_session_ce.html",
        {
            "lesson": lesson,
            "exercises_json": exercises_json,
            "total_exercises": len(exercises),
        },
    )
