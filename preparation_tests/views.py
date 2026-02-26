from __future__ import annotations

# =========================================================
# 📦 IMPORTS STANDARD
# =========================================================
import json
from pathlib import Path

# =========================================================
# 📦 IMPORTS DJANGO
# =========================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (
    Http404,
    FileResponse,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_POST

# =========================================================
# 📦 MODELS
# =========================================================
from .models import (
    CEFRCertificate,
    CoachIAReport,
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
    UserLessonProgress,
    UserExerciseProgress,
)

# =========================================================
# 🧠 SERVICES MÉTIER
# =========================================================
from preparation_tests.services.feedback import build_smart_feedback
from preparation_tests.services.recommendations import recommend_lessons
from preparation_tests.services.level_engine import get_cefr_progress
from preparation_tests.services.study_plan import (
    build_study_plan,
    adapt_study_plan,
    advance_study_day,
)

# =========================================================
# 🤖 IA
# =========================================================
from preparation_tests.services.ai_coach import get_ai_coach
from preparation_tests.services.ai_coach.coach_global import AICoachGlobal

# =========================================================
# 🔧 CORE
# =========================================================
from core.constants import LEVEL_ORDER


# =========================================================
# 🔧 OUTILS INTERNES
# =========================================================
def _next_unanswered_question(attempt: Attempt):
    answered = set(attempt.answers.values_list("question_id", flat=True))
    return (
        attempt.section.questions
        .exclude(id__in=answered)
        .order_by("id")
        .first()
    )


def _audio_url_from_question(q: Question):
    """
    Retourne l'URL audio si présente
    """
    try:
        if q.asset and q.asset.kind == "audio" and q.asset.file:
            return q.asset.file.url
    except Exception:
        pass
    return None


# =========================================================
# 🏠 ACCUEIL & HUBS
# =========================================================
@login_required
def home(request):
    return render(request, "preparation_tests/home.html")


@login_required
def french_exams(request):
    return render(request, "preparation_tests/french_exams.html")


@login_required
def tef_hub(request):
    sections = [
        {"code": "co", "title": "Compréhension orale"},
        {"code": "ce", "title": "Compréhension écrite"},
        {"code": "ee", "title": "Expression écrite"},
        {"code": "eo", "title": "Expression orale"},
    ]

    for s in sections:
        s["url"] = reverse(
            "preparation_tests:course_section",
            args=["tef", s["code"]],
        )

    return render(
        request,
        "preparation_tests/fr_tef_hub.html",
        {"sections": sections},
    )


@login_required
def tcf_hub(request):
    sections = [
        {"code": "co", "title": "Compréhension orale"},
        {"code": "ce", "title": "Compréhension écrite"},
        {"code": "ee", "title": "Expression écrite"},
        {"code": "eo", "title": "Expression orale"},
    ]

    for s in sections:
        s["url"] = reverse(
            "preparation_tests:course_section",
            args=["tcf", s["code"]],
        )

    return render(
        request,
        "preparation_tests/fr_tcf_hub.html",
        {"sections": sections},
    )


@login_required
def delf_hub(request):
    return render(request, "preparation_tests/fr_delf_hub.html")


# =========================================================
# 📚 EXAMENS
# =========================================================
@login_required
def exam_list(request):
    exams = Exam.objects.all().order_by("language", "name")
    return render(request, "preparation_tests/exam_list.html", {"exams": exams})


@login_required
def exam_detail(request, exam_code):
    exam = get_object_or_404(Exam, code__iexact=exam_code)
    sections = exam.sections.all()
    return render(
        request,
        "preparation_tests/exam_detail.html",
        {"exam": exam, "sections": sections},
    )


# =========================================================
# 📖 COURS PAR SECTION
# =========================================================
@login_required
def course_section(request, exam_code, section):
    exam_code = exam_code.upper()
    exam = get_object_or_404(Exam, code__iexact=exam_code)

    lessons = CourseLesson.objects.filter(
        exams=exam,
        section=section,
        is_published=True
    ).order_by("level", "order")

    cefr = get_cefr_progress(
        user=request.user,
        exam_code=exam.code,
        skill=section,
    )

    return render(
        request,
        "preparation_tests/course_section.html",
        {
            "exam": exam,
            "exam_code": exam.code,
            "section": section,
            "lessons": lessons,
            "cefr": cefr,
        }
    )


# =========================================================
# 📘 LEÇON + EXERCICES
# =========================================================
@login_required
def lesson_session(request, exam_code, section, lesson_id):
    """
    Affiche une leçon avec ses exercices.
    """
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    user = request.user

    raw_exercises = CourseExercise.objects.filter(
        lesson=lesson,
        is_active=True,
    ).order_by("order")

    # Progression utilisateur sur cette leçon
    ulp = UserLessonProgress.objects.filter(user=user, lesson=lesson).first()
    progress_completed = ulp.completed_exercises if ulp else 0
    progress_total = raw_exercises.count()
    progress_percent = ulp.percent if ulp else 0

    # Premium : tous les utilisateurs connectés ont accès audio (à ajuster avec billing)
    is_premium = True

    # Structure attendue par le template : row.obj + row.can_audio
    exercises = [
        {"obj": ex, "can_audio": is_premium}
        for ex in raw_exercises
    ]

    context = {
        "lesson": lesson,
        "exercises": exercises,
        "exam_code": exam_code,
        "display_exam_code": exam_code.upper(),
        "section": section,
        "progress_completed": progress_completed,
        "progress_total": progress_total,
        "progress_percent": progress_percent,
        "is_premium": is_premium,
    }

    return render(request, "preparation_tests/lesson_session.html", context)


# =========================================================
# 🕒 SESSIONS
# =========================================================
@login_required
def start_session_generic(request, exam_code):
    exam = get_object_or_404(Exam, code__iexact=exam_code)
    section = exam.sections.order_by("order").first()

    if not section:
        messages.error(request, "Aucune section disponible.")
        return redirect("preparation_tests:exam_detail", exam_code=exam.code)

    session = Session.objects.create(
        user=request.user,
        exam=exam,
        mode="practice",
    )

    attempt = Attempt.objects.create(
        session=session,
        section=section,
    )

    return redirect("preparation_tests:take_section", attempt_id=attempt.id)


@login_required
def start_session(request, exam_code):
    return start_session_generic(request, exam_code=exam_code)


@login_required
def start_session_with_section(request, exam_code, section):
    return start_session_generic(request, exam_code=exam_code)


# =========================================================
# ❓ QUESTIONS
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

        if hasattr(attempt, "ended_at"):
            attempt.ended_at = timezone.now()

        attempt.save()

        attempt.session.completed_at = timezone.now()
        attempt.session.save()

        return redirect("preparation_tests:session_result", session_id=attempt.session.id)

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


@login_required
def submit_answer(request, attempt_id, question_id):
    if request.method != "POST":
        raise Http404()

    attempt = get_object_or_404(Attempt, id=attempt_id, session__user=request.user)
    question = get_object_or_404(Question, id=question_id)

    choice_id = request.POST.get("choice")
    is_correct = False

    if choice_id:
        choice = get_object_or_404(Choice, id=choice_id, question=question)
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

    total_items = sum(a.total_items or 0 for a in attempts)
    total_correct = sum(a.raw_score or 0 for a in attempts)
    global_pct = int(round(100 * total_correct / total_items)) if total_items else 0

    per_section = {}
    for a in attempts:
        per_section[a.section.code.upper()] = {
            "pct": int(round(100 * a.raw_score / a.total_items)) if a.total_items else 0,
            "correct": a.raw_score,
            "total": a.total_items,
        }

    feedback = build_smart_feedback(
        exam_code=session.exam.code,
        global_pct=global_pct,
        per_section=per_section,
        unlocked_info=None,
    )

    recommended_lessons = recommend_lessons(
        user=request.user,
        exam_code=session.exam.code,
        per_section=per_section,
    )

    analysis = None
    global_analysis = None
    cefr = None

    if attempts.exists():
        global_analysis = AICoachGlobal.analyze_session(attempts)

        first_attempt = attempts.first()
        coach = get_ai_coach(first_attempt.section.code)
        if coach:
            analysis = coach.analyze_attempt(first_attempt)

        cefr = get_cefr_progress(
            user=request.user,
            exam_code=session.exam.code,
            skill=first_attempt.section.code,
        )

    return render(
        request,
        "preparation_tests/result.html",
        {
            "session": session,
            "attempts": attempts,
            "global_pct": global_pct,
            "analysis": analysis,
            "global_analysis": global_analysis,
            "feedback": feedback,
            "recommended_lessons": recommended_lessons,
            "cefr": cefr,
        },
    )


@login_required
def session_correction(request, session_id):
    return redirect("preparation_tests:session_result", session_id=session_id)


@login_required
def session_skill_analysis(request, session_id):
    return redirect("preparation_tests:session_result", session_id=session_id)


@login_required
def session_review(request):
    return render(request, "preparation_tests/session_review.html", {"sessions": []})


@login_required
def retry_wrong_questions(request, session_id):
    return redirect("preparation_tests:session_result", session_id=session_id)


@login_required
def run_retry_session(request, session_id):
    return redirect("preparation_tests:session_result", session_id=session_id)


@login_required
def retry_session_errors(request, session_id):
    session = get_object_or_404(Session, id=session_id, user=request.user)
    return redirect("preparation_tests:session_result", session_id=session.id)


@login_required
def save_lesson_progress(request):
    return JsonResponse({"status": "ok"})


# =========================================================
# 📜 CERTIFICATS
# =========================================================
@login_required
def download_certificate(request, exam_code, level):
    cert_dir = Path(settings.MEDIA_ROOT) / "certificates"
    for file in cert_dir.glob(f"{exam_code}_{level}_*.pdf"):
        return FileResponse(open(file, "rb"), as_attachment=True, filename=file.name)
    raise Http404("Certificat introuvable")


@login_required
def verify_certificate(request, public_id):
    certificate = get_object_or_404(CEFRCertificate, public_id=public_id)
    return render(
        request,
        "preparation_tests/certificate_verify.html",
        {"certificate": certificate},
    )


# =========================================================
# 🎓 EXAMEN BLANC (MOCK EXAM)
# =========================================================
@login_required
def start_mock_exam(request, exam_code, section_code):
    exam = get_object_or_404(Exam, code=exam_code)
    section = get_object_or_404(ExamSection, exam=exam, code=section_code)

    session = Session.objects.create(
        user=request.user,
        exam=exam,
        section=section,
        mode="mock",
    )

    Attempt.objects.create(
        session=session,
        section=section,
    )

    return redirect("preparation_tests:mock_exam_session", session_id=session.id)


@login_required
def mock_exam_session(request, session_id):
    session = get_object_or_404(
        Session,
        id=session_id,
        user=request.user,
        mode="mock",
    )

    exam = session.exam
    section = session.section

    questions = Question.objects.filter(section=section).order_by("?")[:25]

    attempt, _ = Attempt.objects.get_or_create(
        session=session,
        section=section,
        defaults={
            "total_items": questions.count(),
            "raw_score": 0,
            "score_percent": 0,
        },
    )

    cefr = get_cefr_progress(
        user=request.user,
        exam_code=exam.code,
        skill=section.code,
    )

    context = {
        "session": session,
        "exam": exam,
        "exam_code": exam.code,
        "section": section.code,
        "questions": questions,
        "attempt": attempt,
        "cefr": cefr,
    }

    return render(request, "preparation_tests/mock_exam_session.html", context)


@login_required
def mock_exam_results(request, session_id):
    session = get_object_or_404(Session, id=session_id, user=request.user)
    attempt = session.attempts.first()

    correct = attempt.answers.filter(is_correct=True).count()
    total = attempt.total_items
    score = round((correct / total) * 100, 2) if total else 0

    attempt.raw_score = correct
    attempt.score_percent = score
    attempt.save()

    session.total_score = score
    session.completed_at = timezone.now()
    session.save()

    return render(
        request,
        "preparation_tests/mock_exam_results.html",
        {
            "session": session,
            "score": score,
            "correct": correct,
            "total": total,
        },
    )


# =========================================================
# 📊 TABLEAU DE BORD GLOBAL
# =========================================================
@login_required
def dashboard_global(request):
    user = request.user

    progresses = UserSkillProgress.objects.filter(user=user)

    exams = {}
    for p in progresses:
        exams.setdefault(p.exam_code, []).append(p)

    exam_stats = []
    for exam_code, items in exams.items():
        avg_score = round(
            sum(i.score_percent for i in items) / len(items)
        ) if items else 0

        max_level = max(
            items,
            key=lambda x: list(LEVEL_ORDER.keys()).index(x.current_level)
        ).current_level

        exam_stats.append({
            "exam": exam_code.upper(),
            "avg_score": avg_score,
            "level": max_level,
        })

    if progresses.exists():
        global_index = max(
            list(LEVEL_ORDER.keys()).index(p.current_level)
            for p in progresses
        )
    else:
        global_index = 0

    global_level = list(LEVEL_ORDER.keys())[global_index]
    global_progress = round(global_index / (len(LEVEL_ORDER) - 1) * 100)

    skills = {"co": 0, "ce": 0, "ee": 0, "eo": 0}
    counts = {"co": 0, "ce": 0, "ee": 0, "eo": 0}

    for p in progresses:
        if p.skill in skills:
            skills[p.skill] += p.score_percent
            counts[p.skill] += 1

    for k in skills:
        skills[k] = round(skills[k] / counts[k]) if counts[k] else 0

    certificates = CEFRCertificate.objects.filter(user=user)

    latest_sessions = (
        Session.objects
        .filter(user=user, completed_at__isnull=False)
        .prefetch_related("attempts", "attempts__section")
        .order_by("-completed_at")[:3]
    )

    global_ai_analysis = None

    if latest_sessions.exists():
        all_attempts = []
        for session in latest_sessions:
            all_attempts.extend(list(session.attempts.all()))

        if all_attempts:
            global_ai_analysis = AICoachGlobal.analyze_session(all_attempts)

            CoachIAReport.objects.create(
                user=user,
                exam_code=latest_sessions.first().exam.code.upper(),
                scope="global",
                data=global_ai_analysis,
                score_snapshot=skills,
            )

    context = {
        "global_level": global_level,
        "global_progress": global_progress,
        "exam_stats": exam_stats,
        "skills": skills,
        "certificates": certificates,
        "context_global_ai": global_ai_analysis,
    }

    return render(request, "preparation_tests/dashboard_global.html", context)


# =========================================================
# 📅 PLAN D'ÉTUDE PERSONNALISÉ
# =========================================================
@login_required
def study_plan_view(request, exam_code):
    """
    Affiche le plan d'étude personnalisé de l'utilisateur
    """
    plan = build_study_plan(user=request.user, exam_code=exam_code)

    if not plan:
        messages.error(request, "Impossible de charger ton plan d'étude.")
        return redirect("preparation_tests:exam_detail", exam_code=exam_code)

    try:
        last_results = UserSkillResult.objects.filter(
            user=request.user,
            exam__code__iexact=exam_code,
        )

        per_section = {}
        for r in last_results:
            if r.section:
                per_section[r.section.code.upper()] = {"pct": r.score_percent}

        if per_section:
            plan = adapt_study_plan(plan_data=plan, per_section=per_section)

    except Exception:
        pass

    return render(
        request,
        "preparation_tests/study_plan.html",
        {"exam_code": exam_code, "plan": plan},
    )


@login_required
def complete_study_day(request, exam_code):
    """
    Valider la journée d'étude en cours
    """
    advance_study_day(user=request.user, exam_code=exam_code)
    messages.success(request, "Journée validée. Continue comme ca !")
    return redirect("preparation_tests:study_plan", exam_code=exam_code)


# =========================================================
# 🤖 HISTORIQUE COACH IA
# =========================================================
@login_required
def coach_ai_history(request):
    reports = request.user.coach_reports.all()
    return render(
        request,
        "preparation_tests/coach_ai_history.html",
        {"reports": reports},
    )


@login_required
def coach_ai_pdf(request, report_id):
    from preparation_tests.services.coach_ai_pdf import generate_coach_ai_pdf

    report = get_object_or_404(CoachIAReport, id=report_id, user=request.user)
    pdf_path = generate_coach_ai_pdf(report)

    return FileResponse(open(pdf_path, "rb"), as_attachment=True, filename=pdf_path.name)


# =========================================================
# ✅ HUB CO / CE PAR NIVEAU
# =========================================================
@login_required
def co_hub(request):
    user = request.user

    levels = (
        CourseLesson.objects.filter(section="co", is_published=True)
        .values_list("level", flat=True)
        .distinct()
        .order_by("level")
    )

    levels_data = []
    for level in levels:
        total_lessons = CourseLesson.objects.filter(
            section="co", level=level, is_published=True
        ).count()
        completed_lessons = UserLessonProgress.objects.filter(
            user=user, lesson__section="co", lesson__level=level, is_completed=True
        ).count()

        progress_pct = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        levels_data.append({
            "level": level,
            "completed": completed_lessons,
            "total": total_lessons,
            "progress_pct": progress_pct,
        })

    return render(request, "preparation_tests/co_hub.html", {"levels": levels_data})


@login_required
def co_by_level(request, level):
    level = level.upper()
    user = request.user

    lessons = CourseLesson.objects.filter(
        section="co", level=level, is_published=True
    ).order_by("order")

    try:
        cefr = get_cefr_progress(user=user, exam_code="CECR", skill="co")
    except Exception:
        cefr = None

    return render(
        request,
        "preparation_tests/co_by_level.html",
        {
            "section": "co",
            "level": level,
            "lessons": lessons,
            "cefr": cefr,
        },
    )


@login_required
def ce_hub(request):
    user = request.user

    levels = (
        CourseLesson.objects.filter(section="ce", is_published=True)
        .values_list("level", flat=True)
        .distinct()
        .order_by("level")
    )

    levels_data = []
    for level in levels:
        total_lessons = CourseLesson.objects.filter(
            section="ce", level=level, is_published=True
        ).count()
        completed_lessons = UserLessonProgress.objects.filter(
            user=user, lesson__section="ce", lesson__level=level, is_completed=True
        ).count()

        progress_pct = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        levels_data.append({
            "level": level,
            "completed": completed_lessons,
            "total": total_lessons,
            "progress_pct": progress_pct,
        })

    return render(request, "preparation_tests/ce_hub.html", {"levels": levels_data})


@login_required
def ce_by_level(request, level):
    level = level.upper()
    user = request.user

    lessons = CourseLesson.objects.filter(
        section="ce", level=level, is_published=True
    ).order_by("order")

    try:
        cefr = get_cefr_progress(user=user, exam_code="CECR", skill="ce")
    except Exception:
        cefr = None

    return render(
        request,
        "preparation_tests/ce_by_level.html",
        {
            "section": "ce",
            "level": level,
            "lessons": lessons,
            "cefr": cefr,
        },
    )


# =========================================================
# 📈 PROGRESSION EXERCICES (API)
# =========================================================
@login_required
@require_POST
def exercise_progress(request):
    """
    Reçoit: {exercise_id: int, selected: "A", correct: true/false}
    Met à jour UserExerciseProgress + UserLessonProgress.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    exercise_id = payload.get("exercise_id")
    selected = (payload.get("selected") or "").upper()
    correct = bool(payload.get("correct"))

    if not exercise_id:
        return JsonResponse({"ok": False, "error": "missing_exercise_id"}, status=400)

    exercise = CourseExercise.objects.select_related("lesson").filter(id=exercise_id).first()
    if not exercise:
        return JsonResponse({"ok": False, "error": "exercise_not_found"}, status=404)

    lesson = exercise.lesson
    user = request.user

    prog, _ = UserExerciseProgress.objects.get_or_create(
        user=user,
        exercise=exercise,
        defaults={"lesson": lesson},
    )

    if prog.lesson_id != lesson.id:
        prog.lesson = lesson

    prog.mark_attempt(selected=selected, correct=correct)
    prog.save()

    total = lesson.exercises.filter(is_active=True).count()
    completed = UserExerciseProgress.objects.filter(
        user=user,
        lesson=lesson,
        is_completed=True
    ).count()

    percent = int(round((completed / total) * 100)) if total else 0
    is_completed = (total > 0 and completed >= total)

    ulp, _ = UserLessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson,
        defaults={
            "percent": 0,
            "is_completed": False,
            "completed_exercises": 0,
            "total_exercises": total,
        }
    )

    ulp.total_exercises = total
    ulp.completed_exercises = completed
    ulp.percent = percent
    ulp.is_completed = is_completed
    ulp.save()

    return JsonResponse({
        "ok": True,
        "lesson_id": lesson.id,
        "total_exercises": total,
        "completed_exercises": completed,
        "percent": percent,
        "is_completed": is_completed,
        "exercise_completed": prog.is_completed,
        "attempts": prog.attempts,
    })
