from __future__ import annotations

# =========================================================
# 📦 IMPORTS STANDARD
# =========================================================
import json
import unicodedata

# =========================================================
# 📦 IMPORTS DJANGO
# =========================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

# =========================================================
# 🤖 IA
# =========================================================
from .ai_coach import AICoachCO

# =========================================================
# 📦 MODELS
# =========================================================
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
    UserSkillResult,
    UserSkillProgress,
)

# =========================================================
# 🔧 OUTILS INTERNES
# =========================================================

def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _next_unanswered_question(attempt: Attempt):
    answered = set(attempt.answers.values_list("question_id", flat=True))
    return (
        attempt.section.questions
        .exclude(id__in=answered)
        .order_by("id")
        .first()
    )


def _audio_url_from_question(q: Question):
    try:
        if q.asset and q.asset.kind == "audio":
            return q.asset.url
    except Exception:
        pass
    return getattr(q, "audio_url", None)


def _build_exercises_for_lesson(lesson, type_code=None):
    exercises = []
    qs = CourseExercise.objects.filter(
        lesson=lesson,
        is_active=True
    ).order_by("order", "id")

    for ex in qs:
        options = {}
        if ex.option_a: options["A"] = ex.option_a
        if ex.option_b: options["B"] = ex.option_b
        if ex.option_c: options["C"] = ex.option_c
        if ex.option_d: options["D"] = ex.option_d

        exercises.append({
            "type": type_code or lesson.section,
            "instruction": ex.instruction or "",
            "text": ex.passage.text if ex.passage else "",
            "question": ex.question_text,
            "options": options,
            "correct": ex.correct_option,
            "explanation": ex.summary or "",
            "audio_url": ex.audio.url if ex.audio else "",
        })
    return exercises

# =========================================================
# 🏠 ACCUEIL / HUBS
# =========================================================

def home(request):
    return render(request, "preparation_tests/home.html")


def french_exams(request):
    """
    HUB FRANÇAIS (TEF / TCF / DELF-DALF)
    """
    return render(request, "preparation_tests/french_exams.html")


def tef_hub(request):
    return render(request, "preparation_tests/fr_tef_hub.html")


def tcf_hub(request):
    return render(request, "preparation_tests/fr_tcf_hub.html")


def delf_hub(request):
    return render(request, "preparation_tests/fr_delf_hub.html")

# =========================================================
# 📚 EXAMENS
# =========================================================

def exam_list(request):
    exams = Exam.objects.all().order_by("language", "name")
    return render(request, "preparation_tests/exam_list.html", {"exams": exams})


def exam_detail(request, exam_code):
    exam = get_object_or_404(Exam, code=exam_code)
    return render(
        request,
        "preparation_tests/exam_detail.html",
        {"exam": exam, "sections": exam.sections.all()},
    )

# =========================================================
# 🚀 DÉMARRAGE SESSION GÉNÉRIQUE
# =========================================================

@login_required
def start_session_generic(request, exam_code):
    exam = get_object_or_404(Exam, code=exam_code)

    section = exam.sections.order_by("order").first()
    if not section:
        messages.error(request, "Aucune section disponible.")
        return redirect("preparation_tests:exam_detail", exam_code=exam.code)

    session = Session.objects.create(
        user=request.user,
        exam=exam,
        mode="practice",
    )

    attempt = Attempt.objects.create(session=session, section=section)
    return redirect("preparation_tests:take_section", attempt_id=attempt.id)

# =========================================================
# 🧠 QUESTIONS
# =========================================================

@login_required
def take_section(request, attempt_id):
    attempt = get_object_or_404(
        Attempt,
        id=attempt_id,
        session__user=request.user,
    )

    question = _next_unanswered_question(attempt)

    if not question:
        attempt.total_items = attempt.section.questions.count()
        attempt.raw_score = attempt.answers.filter(is_correct=True).count()
        attempt.ended_at = timezone.now()
        attempt.save()

        attempt.session.completed_at = timezone.now()
        attempt.session.save()

        return redirect(
            "preparation_tests:session_result",
            session_id=attempt.session.id,
        )

    return render(
        request,
        "preparation_tests/question.html",
        {
            "attempt": attempt,
            "question": question,
            "choices": question.choices.all(),
            "audio_url": _audio_url_from_question(question),
            "current_index": attempt.answers.count() + 1,
            "total_questions": attempt.section.questions.count(),
        },
    )

# =========================================================
# ✅ RÉPONSE
# =========================================================

@login_required
def submit_answer(request, attempt_id, question_id):
    if request.method != "POST":
        raise Http404()

    attempt = get_object_or_404(Attempt, id=attempt_id)
    question = get_object_or_404(Question, id=question_id)

    choice_id = request.POST.get("choice")
    is_correct = False

    if choice_id:
        choice = get_object_or_404(Choice, id=choice_id)
        is_correct = choice.is_correct

    Answer.objects.create(
        attempt=attempt,
        question=question,
        payload={"choice_id": choice_id},
        is_correct=is_correct,
    )

    return redirect("preparation_tests:take_section", attempt_id=attempt.id)

# =========================================================
# 📊 RÉSULTATS
# =========================================================

@login_required
def session_result(request, session_id):
    session = get_object_or_404(Session, id=session_id, user=request.user)
    attempts = session.attempts.all()

    total = sum(a.total_items or 0 for a in attempts)
    correct = sum(a.raw_score or 0 for a in attempts)
    pct = int(round(100 * correct / total)) if total else 0

    analysis = None
    if session.exam.code.lower() == "tef":
        co_attempt = attempts.filter(section__code="co").first()
        if co_attempt:
            analysis = AICoachCO.analyze_attempt(co_attempt)

    return render(
        request,
        "preparation_tests/result.html",
        {
            "session": session,
            "attempts": attempts,
            "global_pct": pct,
            "analysis": analysis,
        },
    )

# =========================================================
# 🎯 EXAMEN BLANC TEF CO
# =========================================================

@login_required
def tef_co(request):
    """
    Page des cours TEF – Compréhension Orale
    Affiche les leçons publiées depuis la base de données
    """
    lessons = CourseLesson.objects.filter(
        exam__code__iexact="tef",
        section="co",
        locale="fr",
        is_published=True,
    ).order_by("order", "id")

    return render(
        request,
        "preparation_tests/tef_co.html",
        {
            "lessons": lessons,
        },
    )



    # ⚠️ PAS DE SCORE ICI (calcul plus tard)
    if request.user.is_authenticated:
        UserSkillResult.objects.create(
            user=request.user,
            exam_code="tef",
            skill="co",
            session_type="mock",
            score_percent=0,
            total_questions=exercises.count(),
            correct_answers=0,
        )

    return render(
        request,
        "preparation_tests/tef_co_mock.html",
        {
            "exam": exam,
            "exercises": exercises,
            "duration_minutes": 40,
        },
    )

# =========================================================
# 📊 DASHBOARD TEF
# =========================================================

@login_required
def tef_dashboard(request):
    progress = {
        p.skill: p.score_percent
        for p in UserSkillProgress.objects.filter(
            user=request.user,
            exam_code="tef",
        )
    }

    scores = {
        "co": progress.get("co", 0),
        "ce": progress.get("ce", 0),
        "ee": progress.get("ee", 0),
        "eo": progress.get("eo", 0),
    }

    return render(
        request,
        "preparation_tests/tef_dashboard.html",
        {
            "scores": scores,
            "global_score": round(sum(scores.values()) / 4),
        },
    )

def french_exams(request):
    """
    Hub des examens en français (TEF, TCF, DELF/DALF)
    """
    return render(request, "preparation_tests/french_exams.html")




def tef_ce(request):
    """
    Page des cours TEF – Compréhension écrite
    """
    lessons = CourseLesson.objects.filter(
        exam__code="tef",
        section="ce",
        is_published=True,
        locale="fr",
    ).order_by("order", "id")

    return render(
        request,
        "preparation_tests/tef_ce.html",
        {"lessons": lessons},
    )


def tef_ee(request):
    """
    Page des cours TEF – Expression écrite
    """
    lessons = CourseLesson.objects.filter(
        exam__code="tef",
        section="ee",
        is_published=True,
        locale="fr",
    ).order_by("order", "id")

    return render(
        request,
        "preparation_tests/tef_ee.html",
        {"lessons": lessons},
    )


def tef_eo(request):
    """
    Page des cours TEF – Expression orale
    """
    lessons = CourseLesson.objects.filter(
        exam__code="tef",
        section="eo",
        is_published=True,
        locale="fr",
    ).order_by("order", "id")

    return render(
        request,
        "preparation_tests/tef_eo.html",
        {"lessons": lessons},
    )
def lesson_session_co(request, lesson_id):
    """
    Session d’exercices TEF – Compréhension Orale (CO)
    pour UNE leçon donnée.
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="co",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(
        lesson,
        type_code="co",
    )

    return render(
        request,
        "preparation_tests/tef_session_co.html",
        {
            "lesson": lesson,
            "exercises_json": json.dumps(exercises, ensure_ascii=False),
            "total_exercises": len(exercises),
        },
    )

def lesson_session_ce(request, lesson_id):
    """
    Session d’exercices TEF – Compréhension Écrite (CE)
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="ce",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(lesson, type_code="ce")

    return render(
        request,
        "preparation_tests/tef_session_ce.html",
        {
            "lesson": lesson,
            "exercises_json": json.dumps(exercises, ensure_ascii=False),
            "total_exercises": len(exercises),
        },
    )


def lesson_session_ee(request, lesson_id):
    """
    Session d’exercices TEF – Expression Écrite (EE)
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="ee",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(lesson, type_code="ee")

    return render(
        request,
        "preparation_tests/tef_course_base.html",
        {
            "lesson": lesson,
            "lesson_type": "Expression écrite",
            "exercises_json": json.dumps(exercises, ensure_ascii=False),
            "total_exercises": len(exercises),
        },
    )


def lesson_session_eo(request, lesson_id):
    """
    Session d’exercices TEF – Expression Orale (EO)
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="eo",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(lesson, type_code="eo")

    return render(
        request,
        "preparation_tests/tef_course_base.html",
        {
            "lesson": lesson,
            "lesson_type": "Expression orale",
            "exercises_json": json.dumps(exercises, ensure_ascii=False),
            "total_exercises": len(exercises),
        },
    )
@login_required
def start_mock_tef_co(request):
    """
    Lance un EXAMEN BLANC TEF – Compréhension Orale (CO)
    en utilisant le moteur générique (questions réelles).
    """
    exam = get_object_or_404(Exam, code="tef")

    section = exam.sections.filter(code__iexact="co").first()
    if not section:
        messages.error(request, "Section CO introuvable pour le TEF.")
        return redirect(
            "preparation_tests:exam_detail",
            exam_code=exam.code,
        )

    # Création de la session en mode examen blanc
    session = Session.objects.create(
        user=request.user,
        exam=exam,
        mode="mock",
    )

    # Une tentative = une section
    attempt = Attempt.objects.create(
        session=session,
        section=section,
    )

    # Démarrage de la session
    return redirect(
        "preparation_tests:take_section",
        attempt_id=attempt.id,
    )
@login_required
def start_tcf_training(request, section_code):
    """
    Lance un entraînement TCF pour une section donnée (CO / CE / EE / EO)
    en réutilisant le moteur générique.
    """
    exam = get_object_or_404(Exam, code="tcf")

    # on force la section via la querystring
    query = request.GET.copy()
    query["section"] = section_code
    request.GET = query

    return start_session_generic(request, exam_code=exam.code)

@login_required
def start_tcf_full_exam(request):
    """
    Lance un examen blanc TCF (toutes sections).
    """
    return start_session_generic(request, exam_code="tcf")


@login_required
def start_session(request, exam_code):
    """
    Point d’entrée générique :
    - appelé par /session/start/<exam_code>/
    - redirige vers le moteur générique
    """
    return start_session_generic(request, exam_code=exam_code)
@login_required
def start_session_with_section(request, exam_code, section_code):
    """
    Démarre une session en forçant une section précise (CO / CE / EE / EO).
    """
    query = request.GET.copy()
    query["section"] = section_code
    request.GET = query
    return start_session_generic(request, exam_code=exam_code)


@login_required
def session_correction(request, session_id):
    """
    Affiche le corrigé détaillé d’une session :
    - questions
    - réponses utilisateur
    - bonnes réponses
    """
    session = get_object_or_404(
        Session,
        id=session_id,
        user=request.user,
    )

    answers = (
        Answer.objects
        .filter(attempt__session=session)
        .select_related("question", "attempt", "attempt__section")
        .prefetch_related("question__choices")
        .order_by("attempt__section__code", "question__id")
    )

    corrections = []

    for ans in answers:
        q = ans.question

        # réponse correcte (QCM)
        correct_choice = q.choices.filter(is_correct=True).first()
        correct_answer = correct_choice.text if correct_choice else None

        # réponse utilisateur
        user_answer = None
        if isinstance(ans.payload, dict):
            if "choice_id" in ans.payload:
                try:
                    user_choice = Choice.objects.get(id=ans.payload["choice_id"])
                    user_answer = user_choice.text
                except Choice.DoesNotExist:
                    user_answer = "Choix inconnu"
            else:
                user_answer = ans.payload.get("text")

        corrections.append(
            {
                "section": ans.attempt.section.code.upper(),
                "question": q,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": ans.is_correct,
                "explanation": getattr(q, "explanation", ""),
            }
        )

    return render(
        request,
        "preparation_tests/session_correction.html",
        {
            "session": session,
            "corrections": corrections,
        },
    )
@login_required
def session_skill_analysis(request, session_id):
    """
    Analyse des compétences d'une session :
    - performance par section (CO / CE / EE / EO)
    - pourcentage global
    """
    session = get_object_or_404(
        Session,
        id=session_id,
        user=request.user,
    )

    answers = (
        Answer.objects
        .filter(attempt__session=session)
        .select_related("attempt__section")
    )

    per_section = {}
    total_correct = 0
    total_questions = 0

    for ans in answers:
        section_code = ans.attempt.section.code.upper()

        stats = per_section.setdefault(
            section_code,
            {"total": 0, "correct": 0},
        )

        stats["total"] += 1
        total_questions += 1

        if ans.is_correct:
            stats["correct"] += 1
            total_correct += 1

    # calcul des pourcentages
    for sec, data in per_section.items():
        if data["total"]:
            data["pct"] = int(round(100 * data["correct"] / data["total"]))
        else:
            data["pct"] = 0

    global_pct = (
        int(round(100 * total_correct / total_questions))
        if total_questions
        else 0
    )

    return render(
        request,
        "preparation_tests/session_skill_analysis.html",
        {
            "session": session,
            "per_section": per_section,
            "global_pct": global_pct,
            "total_questions": total_questions,
            "total_correct": total_correct,
        },
    )
@login_required
def session_review(request):
    """
    Tableau de bord des sessions de l’utilisateur :
    - liste des sessions passées
    - scores globaux
    """
    sessions = (
        Session.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")
    )

    data = []

    for s in sessions:
        attempts = s.attempts.all()
        total_correct = sum(a.raw_score or 0 for a in attempts)
        total_items = sum(a.total_items or 0 for a in attempts)

        pct = (
            int(round(100 * total_correct / total_items))
            if total_items
            else None
        )

        data.append(
            {
                "id": s.id,
                "exam": s.exam,
                "mode": s.mode,
                "started_at": s.started_at,
                "total_correct": total_correct,
                "total_items": total_items,
                "pct": pct,
            }
        )

    return render(
        request,
        "preparation_tests/session_review.html",
        {
            "sessions": data,
        },
    )

@login_required
def retry_wrong_questions(request, session_id):
    """
    Crée une nouvelle session contenant uniquement
    les questions ratées d’une session précédente.
    """
    original_session = get_object_or_404(
        Session,
        id=session_id,
        user=request.user,
    )

    wrong_answers = (
        Answer.objects
        .filter(attempt__session=original_session, is_correct=False)
        .select_related("question", "attempt__section")
    )

    if not wrong_answers.exists():
        messages.info(
            request,
            "Aucune erreur à reprendre pour cette session."
        )
        return redirect(
            "preparation_tests:session_result",
            session_id=original_session.id,
        )

    # Nouvelle session spéciale "retry"
    retry_session = Session.objects.create(
        user=request.user,
        exam=original_session.exam,
        mode="retry_errors",
    )

    first_attempt = None

    # On regroupe par section
    sections = {}

    for ans in wrong_answers:
        section = ans.attempt.section
        sections.setdefault(section, set()).add(ans.question_id)

    for section, wrong_qids in sections.items():
        attempt = Attempt.objects.create(
            session=retry_session,
            section=section,
        )

        if first_attempt is None:
            first_attempt = attempt

        # On marque les questions correctes comme déjà répondues
        already_ok = section.questions.exclude(id__in=wrong_qids)

        Answer.objects.bulk_create(
            [
                Answer(
                    attempt=attempt,
                    question=q,
                    is_correct=True,
                    payload={"skipped": True},
                )
                for q in already_ok
            ]
        )

    messages.success(
        request,
        "Nouvelle session créée avec uniquement tes erreurs 💪"
    )

    return redirect(
        "preparation_tests:take_section",
        attempt_id=first_attempt.id,
    )

@login_required
def run_retry_session(request, session_id):
    """
    Lance la session de correction des erreurs
    (questions ratées uniquement).
    """
    session = get_object_or_404(
        Session,
        id=session_id,
        user=request.user,
    )

    attempt = session.attempts.first()
    if not attempt:
        messages.error(request, "Aucune tentative trouvée.")
        return redirect("preparation_tests:session_review")

    # prochaine question non répondue
    question = _next_unanswered_question(attempt)

    if not question:
        session.completed_at = timezone.now()
        session.save(update_fields=["completed_at"])
        return redirect(
            "preparation_tests:session_result",
            session_id=session.id,
        )

    choices = question.choices.all() if question.subtype == "mcq" else None

    return render(
        request,
        "preparation_tests/question.html",
        {
            "attempt": attempt,
            "section": attempt.section,
            "exam": session.exam,
            "question": question,
            "choices": choices,
            "duration_sec": None,
        },
    )
@login_required
def retry_session_errors(request, session_id):
    """
    Alias sécurisé vers retry_wrong_questions.
    Utilisé par certaines routes pour relancer
    une session basée uniquement sur les erreurs.
    """
    return retry_wrong_questions(request, session_id=session_id)


@login_required
def tef_co_mock(request):
    """
    Alias vers start_mock_tef_co pour compatibilité URL
    """
    return start_mock_tef_co(request)
