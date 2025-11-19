from __future__ import annotations
from django.shortcuts import get_object_or_404
from .models import Session, Answer, Question
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
import unicodedata
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Session, Attempt  # adapte si noms différents
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .ai_coach import AICoachCO
# en haut de views.py si pas déjà présent
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch


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
    """Retourne la prochaine question non répondue pour une tentative."""
    answered_ids = set(attempt.answers.values_list("question_id", flat=True))
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


def _build_exercises_for_lesson(
    lesson: CourseLesson,
    *,
    type_code: str | None = None,
) -> list[dict]:
    """
    Construit une liste de dicts d'exercices pour le JS.
    Utilisé pour CO / CE / EE / EO.
    """
    exercises_qs = CourseExercise.objects.filter(
        lesson=lesson,
        is_active=True,
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
                "type": type_code or lesson.section,
                "instruction": ex.instruction or "",
                "text": ex.passage.text if ex.passage else "",
                "question": ex.question_text,
                "options": options,
                "correct": ex.correct_option or "",
                "explanation": ex.summary or "",
                "audio_url": ex.audio.url if ex.audio else "",
                "image_url": ex.image.url if ex.image else "",
            }
        )
    return exercises


# =========================================================
# 🏠 NAVIGATION GÉNÉRALE
# =========================================================

def home(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/home.html")


# =========================================================
# 📝 EXAMENS DISPONIBLES
# =========================================================

def exam_list(request: HttpRequest) -> HttpResponse:
    exams = Exam.objects.all().order_by("language", "name")
    return render(
        request,
        "preparation_tests/exam_list.html",
        {"exams": exams},
    )


def exam_detail(request: HttpRequest, exam_code: str) -> HttpResponse:
    exam = get_object_or_404(Exam, code=exam_code)
    sections = exam.sections.all()
    return render(
        request,
        "preparation_tests/exam_detail.html",
        {"exam": exam, "sections": sections},
    )


# =========================================================
# 🚀 DÉMARRAGE SESSION GÉNÉRIQUE
# =========================================================

@login_required
def start_session_generic(
    request: HttpRequest,
    exam_code: str,
) -> HttpResponse:

    exam = get_object_or_404(Exam, code=exam_code)

    wanted = _norm(request.GET.get("section", ""))
    aliases = {
        "co": {"co", "comprehension orale", "compréhension orale", "listening"},
        "ce": {"ce", "comprehension ecrite", "compréhension écrite", "reading"},
        "ee": {"ee", "expression ecrite", "expression écrite", "writing"},
        "eo": {"eo", "expression orale", "speaking"},
    }

    section = None
    if wanted:
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
        return redirect("preparation_tests:exam_detail", exam_code=exam.code)

    session = Session.objects.create(
        user=request.user,
        exam=exam,
        mode="practice",
    )
    attempt = Attempt.objects.create(session=session, section=section)

    return redirect("preparation_tests:take_section", attempt_id=attempt.id)


# =========================================================
# 🧩 PASSATION DES QUESTIONS (MOTEUR GÉNÉRIQUE)
# =========================================================

@login_required
def take_section(request: HttpRequest, attempt_id: int) -> HttpResponse:
    attempt = get_object_or_404(
        Attempt,
        id=attempt_id,
        session__user=request.user,
    )
    section = attempt.section
    exam = section.exam
    q = _next_unanswered_question(attempt)

    if not q:
        total = section.questions.count()
        correct = attempt.answers.filter(is_correct=True).count()
        attempt.total_items = total
        attempt.raw_score = float(correct)
        attempt.ended_at = timezone.now()
        attempt.save(update_fields=["total_items", "raw_score", "ended_at"])

        attempt.session.completed_at = timezone.now()
        attempt.session.save(update_fields=["completed_at"])

        return redirect(
            "preparation_tests:session_result",
            session_id=attempt.session.id,
        )

    answered_count = attempt.answers.count()
    total_questions = section.questions.count()
    current_index = answered_count + 1

    audio_url = _audio_url_from_question(q)
    choices = q.choices.all() if q.subtype == "mcq" else None

    return render(
        request,
        "preparation_tests/question.html",
        {
            "attempt": attempt,
            "section": section,
            "exam": exam,
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
    request: HttpRequest,
    attempt_id: int,
    question_id: int,
) -> HttpResponse:
    """Soumet la réponse d'une question."""
    if request.method != "POST":
        raise Http404()

    attempt = get_object_or_404(
        Attempt,
        id=attempt_id,
        session__user=request.user,
    )
    question = get_object_or_404(
        Question,
        id=question_id,
        section=attempt.section,
    )

    payload: dict = {}
    is_correct = False

    if question.subtype == "mcq":
        choice_id = request.POST.get("choice")
        if not choice_id:
            messages.error(request, "Veuillez sélectionner une réponse.")
            return redirect("preparation_tests:take_section", attempt_id=attempt.id)

        try:
            choice = Choice.objects.get(id=int(choice_id), question=question)
        except Choice.DoesNotExist:
            messages.error(request, "Choix invalide.")
            return redirect("preparation_tests:take_section", attempt_id=attempt.id)

        is_correct = choice.is_correct
        payload = {"choice_id": choice.id}
    else:
        text = (request.POST.get("text") or "").strip()
        if not text:
            messages.error(request, "Veuillez saisir une réponse.")
            return redirect("preparation_tests:take_section", attempt_id=attempt.id)
        payload = {"text": text}

    Answer.objects.create(
        attempt=attempt,
        question=question,
        payload=payload,
        is_correct=is_correct,
    )

    return redirect("preparation_tests:take_section", attempt_id=attempt.id)


# =========================================================
# 📊 RÉSULTATS DE SESSION (+ COACH IA TEF CO)
# =========================================================

@login_required
def session_result(request: HttpRequest, session_id: int) -> HttpResponse:
    """
    Affiche les résultats d'une session complète :
    - score global
    - détails par section (passés au template via `attempts`)
    - analyse IA spéciale TEF CO (coach compréhension orale)
    """
    # On sécurise : la session doit appartenir à l'utilisateur connecté
    session = get_object_or_404(Session, id=session_id, user=request.user)

    # On récupère toutes les tentatives (sections) de cette session
    attempts = (
        session.attempts
        .select_related("section")
        .all()
    )

    # Calcul du total de questions et du nombre de bonnes réponses
    total_items = sum(a.total_items for a in attempts)
    total_correct = sum(int(a.raw_score) for a in attempts)

    if total_items > 0:
        global_pct = int(round((total_correct / total_items) * 100))
    else:
        global_pct = 0

    # Analyse IA CO uniquement pour TEF (section CO / Listening)
    analysis = None
    if session.exam.code.lower() == "tef":
        co_attempt = (
            attempts.filter(section__code__iexact="co").first()
            or attempts.filter(section__code__iexact="listening").first()
        )
        if co_attempt:
            analysis = AICoachCO.analyze_attempt(co_attempt)

    # On envoie tout au template result.html
    return render(
        request,
        "preparation_tests/result.html",
        {
            "session": session,
            "attempts": attempts,
            "total_items": total_items,
            "total_correct": total_correct,
            "global_pct": global_pct,
            "analysis": analysis,
        },
    )


# =========================================================
# 🌍 HUBS LANGUES / EXAMENS
# =========================================================

def french_exams(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/french_exams.html")


def tef_hub(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/fr_tef_hub.html")



def english_exams(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/english_exams.html")


def german_exams(request: HttpRequest) -> HttpResponse:
    return render(request, "preparation_tests/german_exams.html")


# =========================================================
# 📚 COURS TEF (PAGES LEÇONS CO / CE / EE / EO)
# =========================================================

def tef_co(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef",
            section="co",
            is_published=True,
            locale="fr",
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request,
        "preparation_tests/tef_co.html",
        {"lessons": lessons},
    )


def tef_ce(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef",
            section="ce",
            is_published=True,
            locale="fr",
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request,
        "preparation_tests/tef_ce.html",
        {"lessons": lessons},
    )


def tef_ee(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef",
            section="ee",
            is_published=True,
            locale="fr",
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request,
        "preparation_tests/tef_ee.html",
        {"lessons": lessons},
    )


def tef_eo(request: HttpRequest) -> HttpResponse:
    lessons = (
        CourseLesson.objects.filter(
            exam__code="tef",
            section="eo",
            is_published=True,
            locale="fr",
        )
        .prefetch_related("exercises")
        .order_by("order", "id")
    )
    return render(
        request,
        "preparation_tests/tef_eo.html",
        {"lessons": lessons},
    )


# =========================================================
# 🎯 WRAPPER : START SESSION AVEC SECTION FORCÉE
# =========================================================

def start_session_with_section(
    request: HttpRequest,
    exam_code: str,
    section_code: str,
) -> HttpResponse:
    """
    Redirige vers start_session_generic en injectant la section dans la query.
    """
    query = request.GET.copy()
    query["section"] = section_code
    request.GET = query
    return start_session_generic(request, exam_code)


# =========================================================
# 🟢 START_SESSION — BOUTONS "COMMENCER UNE SESSION"
# =========================================================

@login_required
def start_session(request: HttpRequest, exam_code: str) -> HttpResponse:
    """
    Pour TEF CO : on envoie vers la 1ère leçon CO (mode cours).
    Pour tout le reste : moteur générique (banque de questions).
    """
    section_param = (request.GET.get("section") or "").lower()

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
        return redirect("preparation_tests:tef_co")

    return start_session_generic(request, exam_code)


# =========================================================
# 🧠 SESSIONS PAR LEÇON (CO / CE / EE / EO)
# =========================================================

def lesson_session_co(
    request: HttpRequest,
    lesson_id: int,
) -> HttpResponse:
    """
    Session d'exercices CO pour UNE leçon (TEF).
    Utilise tef_session_co.html.
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="co",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(lesson, type_code="co")
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


def lesson_session_ce(
    request: HttpRequest,
    lesson_id: int,
) -> HttpResponse:
    """
    Session d'exercices CE pour UNE leçon (TEF).
    Utilise tef_session_ce.html.
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="ce",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(lesson, type_code="ce")
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


def lesson_session_eo(
    request: HttpRequest,
    lesson_id: int,
) -> HttpResponse:
    """
    Session d'exercices EO pour UNE leçon (TEF).
    Réutilise le moteur générique tef_course_base.html.
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="eo",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(lesson, type_code="eo")

    context = {
        "lesson": lesson,
        "lesson_type": "Expression orale",
        "total_exercises": len(exercises),
        "exercises_json": json.dumps(exercises, ensure_ascii=False),
    }
    return render(request, "preparation_tests/tef_course_base.html", context)


def lesson_session_ee(
    request: HttpRequest,
    lesson_id: int,
) -> HttpResponse:
    """
    Session d'exercices EE pour UNE leçon (TEF).
    Réutilise tef_course_base.html.
    """
    lesson = get_object_or_404(
        CourseLesson,
        id=lesson_id,
        exam__code="tef",
        section="ee",
        is_published=True,
    )

    exercises = _build_exercises_for_lesson(lesson, type_code="ee")

    context = {
        "lesson": lesson,
        "lesson_type": "Expression écrite",
        "total_exercises": len(exercises),
        "exercises_json": json.dumps(exercises, ensure_ascii=False),
    }
    return render(request, "preparation_tests/tef_course_base.html", context)


# =========================================================
# 🧪 MODE EXAMEN BLANC TEF CO
# =========================================================

@login_required
def start_mock_tef_co(request: HttpRequest) -> HttpResponse:
    """
    Lance un examen blanc TEF CO avec le moteur générique.
    (Session en mode 'mock')
    """
    exam = get_object_or_404(Exam, code="tef")
    section = exam.sections.filter(code__iexact="co").first()
    if not section:
        messages.error(request, "Aucune section CO configurée pour le TEF.")
        return redirect("preparation_tests:exam_detail", exam_code=exam.code)

    session = Session.objects.create(
        user=request.user,
        exam=exam,
        mode="mock",  # utilisé dans le template question.html
    )
    Attempt.objects.create(session=session, section=section)

    return redirect("preparation_tests:take_section", attempt_id=session.attempts.first().id)


# =========================================================
# 📘 CORRIGÉ DÉTAILLÉ + STATS + RECOMMANDATIONS
# =========================================================

@login_required
def session_correction(request: HttpRequest, session_id: int) -> HttpResponse:
    """
    Corrigé détaillé question par question +
    statistiques avancées + recommandations intelligentes.
    """
    # 1) Sécurité : la session doit appartenir à l'utilisateur connecté
    session = get_object_or_404(Session, id=session_id, user=request.user)

    # 2) On récupère toutes les réponses de cette session
    answers = (
        Answer.objects.filter(attempt__session=session)
        .select_related("question", "attempt", "attempt__section")
        .prefetch_related("question__choices")
        .order_by("attempt__section__code", "question_id")
    )

    corrections: list[dict] = []
    raw_stats: dict[str, dict[str, int]] = {}  # ex: {"CO": {"correct": 12, "total": 20}}
    sections: set[str] = set()

    # 3) Construction des corrections + stats brutes par section
    for ans in answers:
        q = ans.question
        sec = ans.attempt.section.code.upper() if ans.attempt and ans.attempt.section else "GEN"
        sections.add(sec)

        if sec not in raw_stats:
            raw_stats[sec] = {"correct": 0, "total": 0}

        raw_stats[sec]["total"] += 1
        if ans.is_correct:
            raw_stats[sec]["correct"] += 1

        # Bonne réponse (QCM)
        correct_choice = q.choices.filter(is_correct=True).first()
        correct_answer = correct_choice.text if correct_choice else None

        # Réponse utilisateur (QCM / texte)
        if isinstance(ans.payload, dict) and ans.payload.get("choice_id"):
            try:
                user_choice = Choice.objects.get(id=ans.payload["choice_id"])
                user_answer = user_choice.text
            except Choice.DoesNotExist:
                user_answer = "Réponse inconnue"
        else:
            if isinstance(ans.payload, dict):
                user_answer = ans.payload.get("text", "Aucune réponse")
            else:
                user_answer = "Aucune réponse"

        # Audio (si question de CO avec asset audio)
        audio_url = _audio_url_from_question(q)

        corrections.append(
            {
                "section": sec,
                "question": q,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": ans.is_correct,
                "explanation": getattr(q, "explanation", None),
                "audio_url": audio_url,
            }
        )

    sections_list = sorted(list(sections))

    # 4) Statistiques globales
    global_correct = sum(raw_stats[s]["correct"] for s in raw_stats) if raw_stats else 0
    global_total = sum(raw_stats[s]["total"] for s in raw_stats) if raw_stats else 0
    global_pct = round((global_correct / global_total) * 100, 1) if global_total else 0

    # 5) Statistiques avancées par section (avec niveau)
    stats_per_section: dict[str, dict] = {}
    for sec, data in raw_stats.items():
        total = data["total"]
        correct = data["correct"]
        pct = round((correct / total) * 100, 1) if total else 0

        # Niveau estimé très simple (tu pourras affiner plus tard)
        if pct < 40:
            level = "A1–A2 (débutant)"
        elif pct < 60:
            level = "B1 (intermédiaire)"
        elif pct < 80:
            level = "B2 (avancé)"
        else:
            level = "C1–C2 (très avancé)"

        stats_per_section[sec] = {
            "total": total,
            "correct": correct,
            "pct": pct,
            "level": level,
        }

    # 6) Recommandations automatiques (texte) à partir des stats
    recommendations: list[dict] = []
    for sec, data in stats_per_section.items():
        pct = data["pct"]

        if pct < 60:
            strength = "faible"
            suggestion = (
                f"Section {sec} : ton taux de réussite est de {pct} %. "
                f"Reprends les cours de base et refais les exercices faciles en notant tes erreurs récurrentes."
            )
        elif pct < 80:
            strength = "moyen"
            suggestion = (
                f"Section {sec} : bon niveau (environ {pct} %), mais tu peux encore progresser. "
                f"Refais les séries d’exercices où tu as hésité et travaille la gestion du temps."
            )
        else:
            strength = "fort"
            suggestion = (
                f"Section {sec} : excellent niveau (≈ {pct} %). "
                f"Continue avec des simulations d’examen complètes pour stabiliser ce niveau."
            )

        # Lien logique vers la page de cours TEF correspondante (réutilisable pour TCF)
        course_link = f"/fr/tef/{sec.lower()}/"

        recommendations.append(
            {
                "section": sec,
                "strength": strength,
                "suggestion": suggestion,
                "link": course_link,
            }
        )

    # La liste simple de textes, utilisée par ton template session_correction.html
    suggestions = [r["suggestion"] for r in recommendations]

    return render(
        request,
        "preparation_tests/session_correction.html",
        {
            "session": session,
            "corrections": corrections,
            "sections": sections_list,
            "stats": raw_stats,              # brut (si besoin futur)
            "stats_per_section": stats_per_section,  # utilisé par le template
            "global_pct": global_pct,
            "global_correct": global_correct,
            "global_total": global_total,
            "recommendations": recommendations,      # structuré (pour plus tard)
            "suggestions": suggestions,              # juste les phrases pour le template
        },
    )

# =========================================================================================
#=======================================================================
# section TCF

# =========================================================
# 🌍 TCF — HUB
# =========================================================

def tcf_hub(request: HttpRequest) -> HttpResponse:
    """
    Hub principal TCF : page d’accueil TCF.
    """
    return render(request, "preparation_tests/fr_tcf_hub.html", {})


# =========================================================
# 🌐 TCF — Entraînements dédiés
# =========================================================

@login_required
def start_tcf_training(request: HttpRequest, section_code: str) -> HttpResponse:
    """
    Lance un entraînement TCF pour UNE section (CO / CE / EE / EO)
    en réutilisant le moteur générique + logique d’alias.
    """
    # on injecte la section dans la querystring, comme pour start_session_with_section
    query = request.GET.copy()
    query["section"] = section_code
    request.GET = query

    # on utilise le moteur générique, mais avec l’examen "tcf"
    return start_session_generic(request, exam_code="tcf")


@login_required
def start_tcf_full_exam(request: HttpRequest) -> HttpResponse:
    """
    Lance une session TCF générale (toutes sections)
    en utilisant le même moteur générique que les autres examens.
    """
    # on réutilise la logique déjà existante : pour TCF il n’y a
    # pas de traitement spécial, ça bascule vers start_session_generic.
    return start_session(request, exam_code="tcf")


# =========================================================
# 📊 TABLEAU DE BORD : MES SESSIONS / STATISTIQUES
# =========================================================



@login_required
def session_review(request):
    """
    Dashboard premium : historique des sessions + stats globales + badges.
    URL : /prep/sessions/
    """

    # =====================================================
    # 1) RÉCUPÉRATION DES SESSIONS
    # =====================================================
    sessions_qs = (
        Session.objects.filter(user=request.user)
        .select_related("exam")
        .prefetch_related("attempts")
        .order_by("-started_at")
    )

    # On construit une liste de dicts pour le template
    sessions = []

    # Stats globales
    total_sessions = sessions_qs.count()
    total_with_score = 0
    sum_pct = 0
    best_pct = 0
    last_pct = None

    # stats par examen (TEF / TCF / autres)
    exams_stats = {}  # {"tef": {...}, "tcf": {...}}

    for idx, s in enumerate(sessions_qs):
        attempts = list(s.attempts.all())
        total_correct = sum(a.raw_score or 0 for a in attempts)
        total_items = sum(a.total_items or 0 for a in attempts)

        if total_items > 0:
            pct_int = int(round(100 * total_correct / total_items))
        else:
            pct_int = None

        # ---------- pour le template ----------
        sessions.append(
            {
                "id": s.id,
                "exam": s.exam,
                "mode": s.mode,
                "started_at": s.started_at,
                "total_correct": total_correct,
                "total_items": total_items,
                "score_pct": pct_int,
            }
        )

        # ---------- pour les stats globales ----------
        if pct_int is not None:
            sum_pct += pct_int
            total_with_score += 1

            if pct_int > best_pct:
                best_pct = pct_int

            # session la plus récente = idx 0
            if idx == 0:
                last_pct = pct_int

            code = (s.exam.code or "").lower()
            stat = exams_stats.setdefault(
                code,
                {"exam": s.exam, "count": 0, "sum_pct": 0, "best_pct": 0},
            )
            stat["count"] += 1
            stat["sum_pct"] += pct_int
            if pct_int > stat["best_pct"]:
                stat["best_pct"] = pct_int

    global_avg = int(round(sum_pct / total_with_score)) if total_with_score else None

    # =====================================================
    # 2) STATS PAR SECTION (CO / CE / EE / EO)
    # =====================================================
    attempts_all = (
        Attempt.objects.filter(session__in=sessions_qs)
        .select_related("section", "session", "section__exam")
    )

    SECTION_LABELS = {
        "CO": "Compréhension orale",
        "CE": "Compréhension écrite",
        "EE": "Expression écrite",
        "EO": "Expression orale",
    }

    section_stats = {}  # "CO": {...}

    for at in attempts_all:
        code = (at.section.code or "").upper()
        total_items = getattr(at, "total_items", 0) or 0
        raw_score = getattr(at, "raw_score", 0) or 0

        if total_items <= 0:
            continue

        pct = int(round(100 * raw_score / total_items))

        # 🔁 ICI ON NE TOUCHE PLUS À section.name (qui n’existe pas)
        label = SECTION_LABELS.get(code, f"Section {code}")

        st = section_stats.setdefault(
            code,
            {
                "code": code,
                "label": label,
                "sum_pct": 0,
                "count": 0,
                "best_pct": 0,
            },
        )
        st["sum_pct"] += pct
        st["count"] += 1
        if pct > st["best_pct"]:
            st["best_pct"] = pct

    # moyenne par section
    for st in section_stats.values():
        if st["count"]:
            st["avg_pct"] = int(round(st["sum_pct"] / st["count"]))
        else:
            st["avg_pct"] = None

    # =====================================================
    # 3) MINI TIMELINE (HISTORIQUE VISUEL)
    # =====================================================
    timeline = []
    last_sessions = list(sessions_qs[:8])[::-1]  # du plus ancien au plus récent
    for s in last_sessions:
        attempts = list(s.attempts.all())
        total_correct = sum(a.raw_score or 0 for a in attempts)
        total_items = sum(a.total_items or 0 for a in attempts)
        if total_items > 0:
            pct = int(round(100 * total_correct / total_items))
        else:
            pct = None

        timeline.append(
            {
                "date": s.started_at.strftime("%d/%m"),
                "exam": s.exam.code.upper(),
                "pct": pct,
            }
        )

    # =====================================================
    # 4) BADGES
    # =====================================================
    badges = []

    if total_sessions >= 5:
        badges.append(
            {
                "kind": "gold",
                "title": "Marathonien(ne)",
                "text": "Tu as effectué au moins 5 sessions – belle régularité.",
            }
        )
    if global_avg and global_avg >= 70:
        badges.append(
            {
                "kind": "gold",
                "title": "Score solide",
                "text": f"Moyenne générale de {global_avg} % ou plus.",
            }
        )

    for code, st in section_stats.items():
        if st["count"] >= 3 and st["avg_pct"] >= 80:
            badges.append(
                {
                    "kind": "section",
                    "title": f"{code} 80 % +",
                    "text": (
                        f"Tu maîtrises bien la section {code} "
                        f"(moyenne {st['avg_pct']} % sur {st['count']} tentatives)."
                    ),
                }
            )

    context = {
        "sessions": sessions,  # ⚠️ liste de dicts compatible avec ton template
        "global_stats": {
            "total_sessions": total_sessions,
            "global_avg": global_avg,
            "best_pct": best_pct,
            "last_pct": last_pct,
            "tef_avg": int(
                round(exams_stats["tef"]["sum_pct"] / exams_stats["tef"]["count"])
            )
            if "tef" in exams_stats and exams_stats["tef"]["count"]
            else None,
            "tcf_avg": int(
                round(exams_stats["tcf"]["sum_pct"] / exams_stats["tcf"]["count"])
            )
            if "tcf" in exams_stats and exams_stats["tcf"]["count"]
            else None,
        },
        "section_stats": list(section_stats.values()),
        "timeline": timeline,
        "badges": badges,
    }

    return render(request, "preparation_tests/session_review.html", context)


######################################

def retry_wrong_questions(request, session_id):
    old_session = get_object_or_404(Session, id=session_id)

    # récupérer toutes les erreurs
    wrong_answers = Answer.objects.filter(
        attempt__session=old_session,
        is_correct=False
    )

    if not wrong_answers.exists():
        messages.info(request, "Aucune erreur à recommencer.")
        return redirect("preparation_tests:session_result", session_id=old_session.id)

    # extraire la liste unique des questions
    questions = Question.objects.filter(id__in=wrong_answers.values_list("question_id"))

    # créer une nouvelle session
    new_session = Session.objects.create(
        user=request.user if request.user.is_authenticated else None,
        exam=old_session.exam,
        mode="retry_errors"  # MODE SPÉCIAL
    )

    # créer un seul Attempt regroupant toutes les questions
    attempt = new_session.attempt_set.create(
        section="retry",
        total_items=questions.count(),
    )

    # on stocke la liste des questions dans l'ordre
    request.session[f"retry_questions_{new_session.id}"] = list(questions.values_list("id", flat=True))

    return redirect("preparation_tests:run_retry_session", session_id=new_session.id)






def run_retry_session(request: HttpRequest, session_id: int) -> HttpResponse:
    """
    Mini-session spéciale : uniquement les questions que l'utilisateur a ratées
    dans une ancienne session.
    """
    session = get_object_or_404(Session, id=session_id, user=request.user)

    # Liste des IDs de questions à rejouer stockée en session Django
    question_ids = request.session.get(f"retry_questions_{session.id}", [])

    if not question_ids:
        messages.info(request, "Aucune question à rejouer dans cette session.")
        return redirect("preparation_tests:session_result", session_id=session.id)

    total = len(question_ids)
    index = int(request.GET.get("q", 0))

    # Fin de la mini-session
    if index >= total:
        session.completed_at = timezone.now()
        session.save(update_fields=["completed_at"])
        return redirect("preparation_tests:session_result", session_id=session.id)

    qid = question_ids[index]
    question = get_object_or_404(Question, id=qid)

    # On suppose un seul attempt pour cette session "retry"
    attempt = session.attempts.first()

    # Soumission de la réponse
    if request.method == "POST":
        choice_id = request.POST.get("choice")
        if not choice_id:
            messages.error(request, "Veuillez sélectionner une réponse.")
        else:
            # On vérifie la réponse à la main
            selected = question.choices.filter(id=choice_id).first()
            is_correct = bool(selected and selected.is_correct)

            Answer.objects.create(
                attempt=attempt,
                question=question,
                payload={"choice_id": int(choice_id)},
                is_correct=is_correct,
            )

            # Question suivante
            return redirect(
                "preparation_tests:run_retry_session",
                session_id=session.id,
            ) + f"?q={index + 1}"

    # On prépare les choix comme dans take_section
    choices = question.choices.all() if question.subtype == "mcq" else None

    return render(
        request,
        "preparation_tests/run_retry.html",
        {
            "session": session,
            "question": question,
            "choices": choices,
            "index": index,
            "total": total,
        },
    )

# =========================================================
# 📈 ANALYSE DE COMPÉTENCES (SESSION)
# =========================================================

@login_required
def session_skill_analysis(request: HttpRequest, session_id: int) -> HttpResponse:
    """
    Analyse de compétences pour une session :
    - stats par section (CO, CE, EE, EO)
    - stats par difficulté (facile / moyen / difficile, etc.)
    - sections et types de questions les plus faibles
    - suggestions de travail
    """
    # 1) Sécurité : la session doit appartenir à l'utilisateur connecté
    session = get_object_or_404(Session, id=session_id, user=request.user)

    # 2) On récupère toutes les réponses de cette session
    answers = (
        Answer.objects.filter(attempt__session=session)
        .select_related("question", "attempt", "attempt__section")
        .order_by("attempt__section__code", "question_id")
    )

    per_section: dict[str, dict] = {}
    per_diff: dict[str, dict] = {}

    # 3) Stats par section + par difficulté
    for ans in answers:
        # Section (CO / CE / EE / EO)
        sec_code = ans.attempt.section.code.upper() if ans.attempt and ans.attempt.section else "GEN"
        sec_data = per_section.setdefault(sec_code, {"total": 0, "correct": 0})
        sec_data["total"] += 1
        if ans.is_correct:
            sec_data["correct"] += 1

        # Difficulté (facile / moyen / difficile...) — ou "STANDARD" par défaut
        difficulty = getattr(ans.question, "difficulty", "") or "standard"
        difficulty = str(difficulty).upper()
        diff_data = per_diff.setdefault(difficulty, {"total": 0, "correct": 0})
        diff_data["total"] += 1
        if ans.is_correct:
            diff_data["correct"] += 1

    # 4) Stats globales
    global_total = sum(d["total"] for d in per_section.values()) if per_section else 0
    global_correct = sum(d["correct"] for d in per_section.values()) if per_section else 0
    global_pct = int(round((global_correct / global_total) * 100)) if global_total else 0

    def _level_from_pct(p: float) -> str:
        if p < 40:
            return "A1–A2 (débutant)"
        if p < 60:
            return "B1 (intermédiaire)"
        if p < 80:
            return "B2 (avancé)"
        return "C1–C2 (très avancé)"

    # 5) Compléter les stats par section
    for data in per_section.values():
        total = data["total"]
        correct = data["correct"]
        pct = round((correct / total) * 100, 1) if total else 0
        data["pct"] = pct
        data["level"] = _level_from_pct(pct)

    # 6) Compléter les stats par difficulté
    for data in per_diff.values():
        total = data["total"]
        correct = data["correct"]
        pct = round((correct / total) * 100, 1) if total else 0
        data["pct"] = pct

    def _label_for_section(code: str) -> str:
        up = code.upper()
        if up == "CO":
            return "Compréhension orale"
        if up == "CE":
            return "Compréhension écrite"
        if up == "EE":
            return "Expression écrite"
        if up == "EO":
            return "Expression orale"
        return f"Section {up}"

    # 7) Construire une liste triée des sections les plus faibles
    weak_sections = []
    for sec_code, data in per_section.items():
        weak_sections.append(
            {
                "code": sec_code,
                "label": _label_for_section(sec_code),
                "pct": data.get("pct", 0),
                "level": data.get("level", ""),
                "total": data.get("total", 0),
                "correct": data.get("correct", 0),
            }
        )
    weak_sections.sort(key=lambda s: s["pct"])

    # 8) Difficultés les plus faibles
    weak_difficulties = []
    for diff, data in per_diff.items():
        weak_difficulties.append(
            {
                "difficulty": diff,
                "pct": data.get("pct", 0),
                "total": data.get("total", 0),
                "correct": data.get("correct", 0),
            }
        )
    weak_difficulties.sort(key=lambda d: d["pct"])

    # 9) Suggestions automatiques
    suggestions: list[str] = []
    if not answers.exists():
        suggestions.append(
            "Aucune réponse enregistrée pour cette session. Lance une nouvelle session pour générer des statistiques."
        )
    else:
        if weak_sections:
            worst = weak_sections[0]
            suggestions.append(
                f"Ta priorité n°1 est la section {worst['label']} (≈ {worst['pct']} %). "
                "Commence par revoir la méthode et refaire des exercices ciblés sur cette compétence."
            )

        low_diffs = [d for d in weak_difficulties if d["pct"] < 60]
        if low_diffs:
            names = ", ".join(d["difficulty"] for d in low_diffs[:3])
            suggestions.append(
                f"Tu fais encore beaucoup d’erreurs sur les questions de type : {names}. "
                "Consacre une session spécifique à ces formats pour les maîtriser."
            )

        suggestions.append(
            "Plan de travail conseillé : 1) revoir le cours de la section la plus faible, "
            "2) refaire 10–15 questions ciblées, 3) analyser à nouveau tes erreurs."
        )

    context = {
        "session": session,
        "per_section": per_section,
        "per_diff": per_diff,
        "weak_sections": weak_sections,
        "weak_difficulties": weak_difficulties,
        "global_total": global_total,
        "global_correct": global_correct,
        "global_pct": global_pct,
        "suggestions": suggestions,
    }
    return render(request, "preparation_tests/session_skill_analysis.html", context)





# ... tes autres imports sont déjà là


@login_required
def retry_session_errors(request: HttpRequest, session_id: int) -> HttpResponse:
    """
    Crée une NOUVELLE session qui contient uniquement
    les questions ratées dans la session d'origine.
    On réutilise le moteur générique question.html.
    """
    original_session = get_object_or_404(
        Session,
        id=session_id,
        user=request.user,
    )

    # Toutes les réponses fausses de cette session
    wrong_answers = (
        Answer.objects
        .filter(attempt__session=original_session, is_correct=False)
        .select_related("question", "attempt__section")
    )

    if not wrong_answers.exists():
        messages.info(
            request,
            "Tu n'as aucune erreur sur cette session. Bravo 👏 !"
        )
        return redirect("preparation_tests:session_result", session_id=original_session.id)

    # Nouvelle session "retry"
    retry_session = Session.objects.create(
        user=request.user,
        exam=original_session.exam,
        mode="retry_errors",  # juste un label, tu peux changer le texte
    )

    # On regroupe les questions ratées par section
    by_section: dict[ExamSection, set[int]] = {}

    for ans in wrong_answers:
        sec = ans.attempt.section  # section de l'ancienne tentative
        if sec not in by_section:
            by_section[sec] = set()
        by_section[sec].add(ans.question_id)

    first_attempt = None

    # Pour chaque section : on crée une nouvelle Attempt
    # et on pré-marque comme "déjà répondues" les questions
    # qui étaient correctes (pour que le moteur ne pose que les erreurs).
    for section, wrong_ids in by_section.items():
        attempt = Attempt.objects.create(
            session=retry_session,
            section=section,
        )

        if first_attempt is None:
            first_attempt = attempt

        # Toutes les questions de la section qui N'ÉTAIENT PAS en erreur
        already_ok_qs = section.questions.exclude(id__in=wrong_ids)

        fake_answers = []
        for q in already_ok_qs:
            fake_answers.append(
                Answer(
                    attempt=attempt,
                    question=q,
                    is_correct=True,
                    payload={"auto_skip": True},  # juste pour info
                )
            )

        if fake_answers:
            Answer.objects.bulk_create(fake_answers)

    if not first_attempt:
        messages.error(
            request,
            "Impossible de reconstruire tes erreurs pour cette session."
        )
        return redirect("preparation_tests:session_result", session_id=original_session.id)

    messages.success(
        request,
        "Nouvelle session créée avec uniquement tes erreurs. On les corrige ensemble 💪."
    )
    return redirect("preparation_tests:take_section", attempt_id=first_attempt.id)


#######################################################################################################
#########################################################################################
###############################################################################################
############### SECTION DELF / DALF


def delf_hub(request):
    """
    Hub DELF & DALF : choix du niveau et accès aux entraînements.
    URL : /prep/fr/delf-dalf/
    """
    return render(request, "preparation_tests/fr_delf_hub.html")



















