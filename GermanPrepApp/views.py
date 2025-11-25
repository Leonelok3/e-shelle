from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Avg, Max
import json
from django.conf import settings
from openai import OpenAI, OpenAIError

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


from .models import (
    GermanExam,
    GermanLesson,
    GermanExercise,
    GermanResource,
    GermanPlacementQuestion,
    GermanTestSession,
    GermanUserAnswer,
    GermanUserProfile,
)

# =============================
# CLIENT OPENAI - COACH IA ALLEMAND
# =============================
OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", None)
german_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _get_or_create_profile(user) -> GermanUserProfile:
    profile, _ = GermanUserProfile.objects.get_or_create(user=user)
    return profile


def _level_from_score(score: float) -> str:
    """
    Convertit le score du test de niveau en recommandation A1–C2.
    """
    if score < 25:
        return "A1"
    if score < 40:
        return "A2"
    if score < 60:
        return "B1"
    if score < 75:
        return "B2"
    if score < 90:
        return "C1"
    return "C2"


# =========================
#  HOME / HUB ALLEMAND
# =========================

@login_required
def home(request):
    profile = _get_or_create_profile(request.user)

    exams = (
        GermanExam.objects
        .filter(is_active=True)
        .order_by("level", "exam_type", "title")
    )

    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    exams_by_level = {lvl: [] for lvl in levels}
    for exam in exams:
        exams_by_level[exam.level].append(exam)

    last_sessions = (
        GermanTestSession.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")[:5]
    )

    context = {
        "profile": profile,
        "exams_by_level": exams_by_level,
        "last_sessions": last_sessions,
    }
    return render(request, "german/home.html", context)


# =========================
#  HUB PAR NIVEAU (A1, A2, B1...)
# =========================

LEVEL_LABELS = {
    "A1": "Débutant absolu",
    "A2": "Élémentaire",
    "B1": "Intermédiaire",
    "B2": "Intermédiaire avancé",
    "C1": "Avancé",
    "C2": "Maîtrise",
}

LEVEL_DESCRIPTIONS = {
    "A1": "Bases de la langue, se présenter, phrases très simples pour survivre au quotidien.",
    "A2": "Communication simple dans des situations courantes, petites phrases du quotidien.",
    "B1": "Niveau solide pour immigration, vie quotidienne et échanges simples au travail.",
    "B2": "Expression plus fluide, compréhension de textes plus longs, utile pour études et emploi.",
    "C1": "Très bon niveau académique et professionnel, maîtrise de textes complexes.",
    "C2": "Maîtrise quasi native, compréhension fine et expression spontanée dans tous les contextes.",
}


@login_required
def level_detail(request, level_code: str):
    """
    Page 'Niveau B1' etc.
    Affiche tous les examens, leçons, ressources et simulations liés à ce niveau.
    """
    level_code = level_code.upper()
    if level_code not in LEVEL_LABELS:
        # Niveau inconnu => 404
        return redirect("germanprep:home")

    profile = _get_or_create_profile(request.user)

    exams = GermanExam.objects.filter(level=level_code, is_active=True)
    lessons = GermanLesson.objects.filter(exam__level=level_code).select_related("exam")
    resources = GermanResource.objects.filter(exam__level=level_code).select_related("exam", "lesson")

    # Derniers tests pour ce niveau
    sessions = (
        GermanTestSession.objects
        .filter(user=request.user, exam__level=level_code)
        .select_related("exam")
        .order_by("-started_at")[:5]
    )

    context = {
        "level_code": level_code,
        "level_label": LEVEL_LABELS[level_code],
        "level_description": LEVEL_DESCRIPTIONS[level_code],
        "profile": profile,
        "exams": exams,
        "lessons": lessons,
        "resources": resources,
        "sessions": sessions,
    }
    return render(request, "german/level_detail.html", context)


# =========================
#  TEST DE NIVEAU (PLACEMENT)
# =========================

@login_required
def placement_test(request):
    profile = _get_or_create_profile(request.user)
    questions = GermanPlacementQuestion.objects.filter(is_active=True).order_by("order", "id")

    if request.method == "POST":
        total = questions.count()
        correct = 0

        for q in questions:
            selected = request.POST.get(f"q_{q.id}")
            if not selected:
                continue
            if selected == q.correct_option:
                correct += 1

        score = (correct / total) * 100 if total > 0 else 0
        recommended_level = _level_from_score(score)

        profile.placement_level = recommended_level
        profile.placement_score = score
        profile.save(update_fields=["placement_level", "placement_score"])

        context = {
            "profile": profile,
            "questions": questions,
            "has_result": True,
            "score": round(score, 1),
            "recommended_level": recommended_level,
        }
        return render(request, "german/placement_test.html", context)

    context = {
        "profile": profile,
        "questions": questions,
        "has_result": False,
    }
    return render(request, "german/placement_test.html", context)


# =========================
#  DÉTAIL D'UN EXAMEN = ESPACE DE COURS
# =========================

@login_required
def exam_detail(request, exam_slug):
    exam = get_object_or_404(GermanExam, slug=exam_slug, is_active=True)
    profile = _get_or_create_profile(request.user)

    lessons = exam.lessons.all()
    exam_resources = exam.resources.filter(lesson__isnull=True)

    last_session = (
        GermanTestSession.objects
        .filter(user=request.user, exam=exam)
        .order_by("-started_at")
        .first()
    )

    context = {
        "exam": exam,
        "lessons": lessons,
        "exam_resources": exam_resources,
        "profile": profile,
        "last_session": last_session,
    }
    return render(request, "german/exam_detail.html", context)


# =========================
#  PAGE D'UNE LEÇON
# =========================

@login_required
def lesson_detail(request, exam_slug, lesson_id):
    exam = get_object_or_404(GermanExam, slug=exam_slug, is_active=True)
    lesson = get_object_or_404(GermanLesson, id=lesson_id, exam=exam)

    resources = lesson.resources.all()
    exercises = lesson.exercises.all()

    context = {
        "exam": exam,
        "lesson": lesson,
        "resources": resources,
        "exercises": exercises,
    }
    return render(request, "german/lesson_detail.html", context)


# =========================
#  SIMULATION D'EXAMEN
# =========================

@login_required
def take_practice_test(request, exam_id):
    """
    Simulation type examen pour un GermanExam donné.
    - utilise les GermanExercise liés aux leçons de cet examen
    - crée une GermanTestSession
    - enregistre les réponses GermanUserAnswer
    - met à jour le profil (XP)
    - redirige vers la page de résultat détaillé
    """
    from .models import GermanExam, GermanExercise, GermanTestSession, GermanUserAnswer

    exam = get_object_or_404(GermanExam, id=exam_id, is_active=True)
    exercises = GermanExercise.objects.filter(lesson__exam=exam).order_by("id")

    if request.method == "POST":
        session = GermanTestSession.objects.create(
            user=request.user,
            exam=exam,
        )

        correct_count = 0
        total = exercises.count()

        for ex in exercises:
            selected = request.POST.get(f"exercise_{ex.id}")
            if not selected:
                continue

            is_correct = (selected == ex.correct_option)
            if is_correct:
                correct_count += 1

            GermanUserAnswer.objects.create(
                session=session,
                exercise=ex,
                selected_option=selected,
                is_correct=is_correct,
            )

        score = (correct_count / total) * 100 if total > 0 else 0
        session.score = score
        session.finished_at = timezone.now()
        session.total_questions = total
        session.correct_answers = correct_count
        session.save()

        # 🔥 Mise à jour du profil + XP gagnée
        profile = _get_or_create_profile(request.user)
        try:
            gained_xp = profile.add_result(score, total)
        except TypeError:
            # si add_result ne renvoie rien ou n'accepte pas la même signature
            gained_xp = None

        request.session["last_german_xp_gain"] = gained_xp

        # 👉 on redirige vers la page de résultat de CETTE session
        return redirect("germanprep:test_result", session_id=session.id)

    context = {
        "exam": exam,
        "exercises": exercises,
    }
    return render(request, "german/take_practice_test.html", context)


@login_required
def german_test_result(request, session_id):
    """
    Résultat détaillé d'une session d'examen allemand :
    - score global
    - bonnes / mauvaises réponses
    - stats par compétence (Hören / Lesen / Schreiben / Sprechen / Grammaire)
    - XP gagnée
    """
    from .models import GermanTestSession, GermanExercise

    session = get_object_or_404(
        GermanTestSession,
        id=session_id,
        user=request.user,
    )
    exam = session.exam

    answers = session.answers.select_related("exercise")
    total = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    incorrect_answers = total - correct_answers

    # Mise à jour des champs si besoin (anciens enregistrements)
    changed = False
    if session.total_questions != total:
        session.total_questions = total
        changed = True
    if session.correct_answers != correct_answers:
        session.correct_answers = correct_answers
        changed = True

    score = session.score
    if score is None and total > 0:
        score = (correct_answers / total) * 100
        session.score = score
        changed = True

    if changed:
        session.save(update_fields=["total_questions", "correct_answers", "score"])

    profile = _get_or_create_profile(request.user)

    # 🔥 XP gagnée sur cette session (si stockée)
    xp_gain = request.session.pop("last_german_xp_gain", None)

    # Stats par compétence
    skill_stats = {}
    label_map = dict(getattr(GermanExercise, "SKILL_CHOICES", []))

    for ans in answers:
        skill = ans.exercise.skill
        stat = skill_stats.setdefault(skill, {"total": 0, "correct": 0})
        stat["total"] += 1
        if ans.is_correct:
            stat["correct"] += 1

    for code, stat in skill_stats.items():
        if stat["total"]:
            pct = int(round(100 * stat["correct"] / stat["total"]))
        else:
            pct = 0
        stat["pct"] = pct
        stat["label"] = label_map.get(code, code)

    context = {
        "session": session,
        "exam": exam,
        "answers": answers,
        "total": total,
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers,
        "score": score or 0,
        "profile": profile,
        "skill_stats": skill_stats,
        "xp_gain": xp_gain,
    }
    return render(request, "german/test_result.html", context)


@login_required
def german_review_incorrect(request, session_id):
    """
    Page spéciale pour revoir uniquement les questions ratées
    d'une session de test allemand.
    """
    from .models import GermanTestSession

    session = get_object_or_404(
        GermanTestSession,
        id=session_id,
        user=request.user,
    )
    exam = session.exam

    answers = session.answers.select_related("exercise")
    incorrect_answers = answers.filter(is_correct=False)
    total = answers.count()
    incorrect_count = incorrect_answers.count()

    if incorrect_count == 0:
        messages.success(
            request,
            "Tu n'as aucune erreur sur ce test d’allemand. Fantastisch ! 🎉",
        )
        return redirect("germanprep:test_result", session_id=session.id)

    context = {
        "session": session,
        "exam": exam,
        "incorrect_answers": incorrect_answers,
        "incorrect_count": incorrect_count,
        "total": total,
    }
    return render(request, "german/review_incorrect.html", context)



@login_required
def german_skill_analysis(request, session_id):
    """
    Analyse des compétences pour UNE session d’allemand :
    - stats par skill (HÖREN, LESEN, SCHREIBEN, SPRECHEN, GRAMMAR_VOCAB, etc.)
    - stats globales
    - mini recommandations texte
    """
    from .models import GermanTestSession, GermanExercise

    session = get_object_or_404(
        GermanTestSession,
        id=session_id,
        user=request.user,
    )
    answers = (
        session.answers
        .select_related("exercise")
    )

    if not answers.exists():
        messages.info(
            request,
            "Aucune réponse enregistrée pour cette session. "
            "Lance une nouvelle simulation pour générer des statistiques.",
        )
        return redirect("germanprep:progress_dashboard")

    skill_stats = {}
    label_map = dict(getattr(GermanExercise, "SKILL_CHOICES", []))

    for ans in answers:
        skill = ans.exercise.skill
        data = skill_stats.setdefault(skill, {"total": 0, "correct": 0})
        data["total"] += 1
        if ans.is_correct:
            data["correct"] += 1

    ordered_skills = []
    for code, data in skill_stats.items():
        total = data["total"]
        correct = data["correct"]
        pct = round((correct / total) * 100, 1) if total else 0.0
        label = label_map.get(code, code)
        ordered_skills.append(
            {
                "code": code,
                "label": label,
                "total": total,
                "correct": correct,
                "pct": pct,
            }
        )

    ordered_skills.sort(key=lambda s: s["pct"])

    global_total = sum(s["total"] for s in ordered_skills)
    global_correct = sum(s["correct"] for s in ordered_skills)
    global_pct = round((global_correct / global_total) * 100, 1) if global_total else 0.0

    # Mini recommandations
    suggestions = []
    if ordered_skills:
        worst = ordered_skills[0]
        suggestions.append(
            f"Ta priorité n°1 est la compétence {worst['label']} "
            f"(≈ {worst['pct']} %). "
            "Revois les leçons et exercices de ce type (Hören/Lesen/Grammaire…) avant de refaire un test."
        )

    if global_pct < 60:
        suggestions.append(
            "Objectif à court terme : dépasser les 60 % sur tes prochaines simulations. "
            "Travaille tous les jours 15–20 minutes plutôt qu'une seule longue session par semaine."
        )
    elif global_pct < 80:
        suggestions.append(
            "Tu as déjà une base correcte. Vise maintenant 75–80 % en retravaillant les compétences les plus faibles "
            "et en refaisant une simulation complète chaque semaine."
        )
    else:
        suggestions.append(
            "Excellent niveau global. Multiplie les tests complets Goethe / telc / TestDaF pour te mettre en condition réelle "
            "et stabiliser ton score."
        )

    profile = _get_or_create_profile(request.user)

    context = {
        "session": session,
        "exam": session.exam,
        "skills": ordered_skills,
        "global_total": global_total,
        "global_correct": global_correct,
        "global_pct": global_pct,
        "suggestions": suggestions,
        "profile": profile,
    }
    return render(request, "german/skill_analysis.html", context)



# =========================
#  TABLEAU DE BORD / COACH IA
# =========================

@login_required
def progress_dashboard(request):
    profile = _get_or_create_profile(request.user)

    sessions = (
        GermanTestSession.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")
    )

    stats_by_level = {}
    for s in sessions:
        lvl = s.exam.level
        stat = stats_by_level.setdefault(
            lvl,
            {"total": 0, "sum_score": 0, "best": 0},
        )
        if s.score is not None:
            stat["total"] += 1
            stat["sum_score"] += s.score
            if s.score > stat["best"]:
                stat["best"] = s.score

    for lvl, stat in stats_by_level.items():
        if stat["total"]:
            stat["avg"] = round(stat["sum_score"] / stat["total"], 1)
        else:
            stat["avg"] = 0

    coach_summary = ""
    coach_plan = []

    weakest_level = None
    strongest_level = None
    if stats_by_level:
        ordered = sorted(
            stats_by_level.items(),
            key=lambda item: item[1]["avg"],
        )
        weakest_level = ordered[0][0]
        strongest_level = ordered[-1][0]

    if profile.placement_level:
        coach_summary = (
            f"Ton dernier test de niveau suggère un niveau {profile.placement_level} "
            f"(score ≈ {profile.placement_score or 0:.1f} %). "
        )
    else:
        coach_summary = "Tu n’as pas encore fait le test de niveau. "

    if weakest_level:
        coach_summary += (
            f"Actuellement, ton niveau le plus fragile semble être {weakest_level}, "
            f"et ton niveau le plus fort est {strongest_level}."
        )
    else:
        coach_summary += (
            "Commence par un premier test ou une simulation pour que je puisse analyser tes résultats."
        )

    if profile.placement_level in ["A1", "A2"]:
        coach_plan.append(
            "1) Pendant 7 jours, travaille les bases A1/A2 : alphabet, saluer, se présenter, "
            "verbes au présent, phrases simples du quotidien."
        )
    elif profile.placement_level in ["B1", "B2"]:
        coach_plan.append(
            "1) Pendant 7 jours, consolide B1/B2 : textes courts, compréhension globale, "
            "structures grammaticales fréquentes (verbes à particule, subordonnées simples)."
        )
    elif profile.placement_level in ["C1", "C2"]:
        coach_plan.append(
            "1) Pendant 7 jours, concentre-toi sur la compréhension de textes longs, "
            "les connecteurs logiques et l’expression écrite argumentée."
        )
    else:
        coach_plan.append(
            "1) Fais le test de niveau pour obtenir une recommandation A1–C2, "
            "puis lance un examen correspondant à ce niveau."
        )

    if weakest_level:
        coach_plan.append(
            f"2) Choisis un examen de niveau {weakest_level} dans le hub allemand et "
            "fais une simulation complète tous les 2–3 jours."
        )
    else:
        coach_plan.append(
            "2) Choisis un examen A1 ou A2 et fais une première simulation pour créer ta base de données."
        )

    coach_plan.append(
        "3) Après chaque simulation, repère les erreurs fréquentes et reviens dans les leçons "
        "(Grammaire, Vocabulaire, Hören/Lesen) liées à ces compétences."
    )
    coach_plan.append(
        "4) Utilise au moins 1 PDF complet et 1 vidéo par semaine dans la section Ressources "
        "de ton niveau pour t’habituer au format réel des examens allemands."
    )
    coach_plan.append(
        "5) Rythme conseillé : 20 à 30 minutes par jour plutôt que de longues sessions une fois par semaine."
    )

    context = {
        "profile": profile,
        "sessions": sessions,
        "stats_by_level": stats_by_level,
        "coach_summary": coach_summary,
        "coach_plan": coach_plan,
    }
    return render(request, "german/progress_dashboard.html", context)



# =========================
#  PALIERS DE NIVEAU (ALLEMAND)
# =========================

LEVEL_THRESHOLDS_GERMAN = [
    (1, 0),
    (2, 100),
    (3, 250),
    (4, 500),
    (5, 900),
    (6, 1400),
]


def _compute_german_level_stats(user):
    """
    Stats par niveau CECRL (A1, A2, B1, B2, C1, C2) pour l'allemand :
    - nombre de tests
    - meilleur score
    - score moyen
    """
    from .models import GermanExam, GermanTestSession  # éviter les imports circulaires

    qs = (
        GermanTestSession.objects
        .filter(user=user, score__isnull=False)
        .select_related("exam")
    )

    stats = {}

    # On boucle sur les niveaux définis dans GermanExam.LEVEL_CHOICES
    for level_code, level_label in getattr(GermanExam, "LEVEL_CHOICES", []):
        sub = qs.filter(exam__level=level_code)
        if not sub.exists():
            continue

        agg = sub.aggregate(
            best=Max("score"),
            avg=Avg("score"),
        )

        stats[level_code] = {
            "label": level_label,
            "count": sub.count(),
            "best": round(agg["best"] or 0.0, 1),
            "avg": round(agg["avg"] or 0.0, 1),
        }

    return stats



@login_required
def german_profile(request):
    """
    Page Profil / progression allemand :
    - XP, niveau, progression vers le prochain niveau
    - Badges
    - Stats par niveau (A1–C2)
    - Derniers tests
    - Recommandation dynamique + preset pour le coach IA
    """
    from .models import GermanTestSession  # import local pour éviter les conflits

    profile = _get_or_create_profile(request.user)

    # ---------- Dernières sessions (timeline) ----------
    sessions = (
        GermanTestSession.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")[:10]
    )

    # ---------- Stats par niveau (A1–C2) ----------
    level_stats = _compute_german_level_stats(request.user)

    # ---------- Progression niveau ----------
    xp = profile.xp or 0
    current_level = profile.level or 1
    thresholds = LEVEL_THRESHOLDS_GERMAN

    current_min_xp = 0
    next_level = current_level + 1
    next_level_xp = None

    for lvl, threshold in thresholds:
        if lvl == current_level:
            current_min_xp = threshold
        if lvl == current_level + 1:
            next_level_xp = threshold

    # si on est au-delà du dernier palier, on étend par blocs de 400 XP
    if next_level_xp is None:
        last_level, last_threshold = thresholds[-1]
        if current_level <= last_level:
            current_min_xp = dict(thresholds).get(current_level, last_threshold)
            next_level_xp = last_threshold + 400
        else:
            extra = current_level - last_level - 1
            current_min_xp = last_threshold + 400 * extra
            next_level_xp = current_min_xp + 400

    xp_in_level = max(0, xp - current_min_xp)
    xp_needed = max(1, next_level_xp - current_min_xp)
    level_progress_pct = int(round(100 * min(xp_in_level / xp_needed, 1)))

    # ---------- Recommandation dynamique ----------
    level_with_lowest_avg = None
    if level_stats:
        level_with_lowest_avg = min(
            level_stats.values(),
            key=lambda s: s["avg"]
        )

    if profile.total_tests == 0:
        next_step = (
            "Commence par un premier test d’allemand niveau A1 ou A2 "
            "pour établir ton niveau de base."
        )
    elif profile.best_score < 60:
        if level_with_lowest_avg:
            next_step = (
                f"Ton point faible actuel semble être le niveau {level_with_lowest_avg['label']} "
                f"(moyenne ≈ {level_with_lowest_avg['avg']} %). "
                "Refais un test dans ce niveau et analyse bien les corrections."
            )
        else:
            next_step = (
                "Tu es en dessous de 60 % en moyenne. "
                "Refais un test d’allemand et essaie de gagner au moins +10 points."
            )
    elif profile.best_score < 80:
        if level_with_lowest_avg:
            next_step = (
                f"Tu as déjà une bonne base. Travaille maintenant le niveau {level_with_lowest_avg['label']} "
                "pour stabiliser tes scores au-dessus de 75 %."
            )
        else:
            next_step = (
                "Continue à enchaîner les tests réguliers et vise des scores stables au-dessus de 75 %."
            )
    else:
        next_step = (
            "Ton niveau global est déjà solide. Enchaîne les tests complets (Goethe, telc, TestDaF) "
            "pour te rapprocher de ton score cible officiel."
        )

    # ---------- Prompt pré-rempli pour le coach IA allemand ----------
    coach_preset = (
        "Analyse mon profil d'allemand sur Immigration97 et propose-moi un plan concret :\n"
        f"- Niveau actuel: {profile.level}\n"
        f"- XP: {profile.xp}\n"
        f"- Meilleur score: {profile.best_score:.1f} %\n"
        f"- Nombre de tests: {profile.total_tests}\n"
    )
    if level_with_lowest_avg:
        coach_preset += (
            f"- Niveau le plus fragile: {level_with_lowest_avg['label']} "
            f"(moyenne ≈ {level_with_lowest_avg['avg']} %)\n"
        )
    coach_preset += (
        "\nDonne-moi :\n"
        "1) Un résumé rapide de mon niveau en allemand.\n"
        "2) Les 2–3 priorités à travailler.\n"
        "3) Un mini-plan sur 7 jours adapté à mon objectif (immigration, études ou travail en Allemagne)."
    )

    context = {
        "profile": profile,
        "sessions": sessions,
        "level_stats": level_stats,
        "level_progress_pct": level_progress_pct,
        "next_level": next_level,
        "current_min_xp": current_min_xp,
        "next_level_xp": next_level_xp,
        "next_step": next_step,
        "coach_preset": coach_preset,
    }
    return render(request, "german/german_profile.html", context)



@login_required
def german_exam_hub(request):
    """
    Hub marketing exam d’allemand :
    - Goethe / telc / TestDaF / DSH / Intégration
    - liens rapides vers les examens et simulations
    """
    from .models import GermanExam, GermanTestSession

    profile = _get_or_create_profile(request.user)

    total_sessions = GermanTestSession.objects.filter(user=request.user).count()
    last_sessions = (
        GermanTestSession.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")[:5]
    )

    goethe_exams = GermanExam.objects.filter(is_active=True, exam_type="GOETHE")
    telc_exams = GermanExam.objects.filter(is_active=True, exam_type="TELC")
    testdaf_exams = GermanExam.objects.filter(is_active=True, exam_type="TESTDAF")
    dsh_exams = GermanExam.objects.filter(is_active=True, exam_type="DSH")
    integration_exams = GermanExam.objects.filter(is_active=True, exam_type="INTEGRATION")

    context = {
        "profile": profile,
        "total_sessions": total_sessions,
        "last_sessions": last_sessions,
        "goethe_exams": goethe_exams,
        "telc_exams": telc_exams,
        "testdaf_exams": testdaf_exams,
        "dsh_exams": dsh_exams,
        "integration_exams": integration_exams,
    }
    return render(request, "german/german_exam_hub.html", context)


@login_required
def german_exam_learning_path(request, exam_slug):
    """
    Page 'Cours & exercices' pour un examen d’allemand donné.
    Affiche toutes les leçons (GermanLesson) + exercices associés,
    idéal pour suivre un parcours structuré par skills.
    """
    from .models import GermanExam, GermanLesson

    exam = get_object_or_404(GermanExam, slug=exam_slug, is_active=True)

    lessons = (
        GermanLesson.objects
        .filter(exam=exam)
        .prefetch_related("exercises", "resources")
        .order_by("skill", "order", "title")
    )

    context = {
        "exam": exam,
        "lessons": lessons,
    }
    return render(request, "german/exam_learning_path.html", context)


@login_required
def german_exam_hub(request):
    """
    Hub marketing exam d’allemand :
    - Goethe / telc / TestDaF / DSH / Intégration
    - liens rapides vers les examens et simulations
    """
    from .models import GermanExam, GermanTestSession

    profile = _get_or_create_profile(request.user)

    total_sessions = GermanTestSession.objects.filter(user=request.user).count()
    last_sessions = (
        GermanTestSession.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")[:5]
    )

    goethe_exams = GermanExam.objects.filter(is_active=True, exam_type="GOETHE")
    telc_exams = GermanExam.objects.filter(is_active=True, exam_type="TELC")
    testdaf_exams = GermanExam.objects.filter(is_active=True, exam_type="TESTDAF")
    dsh_exams = GermanExam.objects.filter(is_active=True, exam_type="DSH")
    integration_exams = GermanExam.objects.filter(is_active=True, exam_type="INTEGRATION")

    context = {
        "profile": profile,
        "total_sessions": total_sessions,
        "last_sessions": last_sessions,
        "goethe_exams": goethe_exams,
        "telc_exams": telc_exams,
        "testdaf_exams": testdaf_exams,
        "dsh_exams": dsh_exams,
        "integration_exams": integration_exams,
    }
    return render(request, "german/german_exam_hub.html", context)
@login_required
def german_exam_learning_path(request, exam_slug):
    """
    Page 'Cours & exercices' pour un examen d’allemand donné.
    Affiche toutes les leçons (GermanLesson) + exercices associés,
    idéal pour suivre un parcours structuré par skills.
    """
    from .models import GermanExam, GermanLesson

    exam = get_object_or_404(GermanExam, slug=exam_slug, is_active=True)

    lessons = (
        GermanLesson.objects
        .filter(exam=exam)
        .prefetch_related("exercises", "resources")
        .order_by("skill", "order", "title")
    )

    context = {
        "exam": exam,
        "lessons": lessons,
    }
    return render(request, "german/exam_learning_path.html", context)


@login_required
def german_ai_coach_page(request):
    """
    Page principale du coach IA pour l’allemand.
    Il récupère le profil d'allemand + la dernière session pour personnaliser le coaching.
    Accepte un paramètre GET ?preset= pour pré-remplir la zone de texte.
    """
    from .models import GermanTestSession

    profile = _get_or_create_profile(request.user)

    last_session = (
        GermanTestSession.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")
        .first()
    )

    preset = (request.GET.get("preset") or "").strip()

    # Si aucun preset envoyé, on peut pré-remplir avec quelque chose d’utile
    if not preset:
        preset = (
            "Je prépare les examens d’allemand sur Immigration97 (Goethe, telc, TestDaF, DSH).\n"
            "Voici mon profil :\n"
            f"- Niveau interne: {profile.level}\n"
            f"- XP: {profile.xp}\n"
            f"- Meilleur score: {profile.best_score:.1f} %\n"
            f"- Nombre de tests: {profile.total_tests}\n"
        )
        if getattr(profile, "placement_level", None):
            preset += f"- Niveau conseillé par le test de niveau: {profile.placement_level}\n"
        preset += (
            "\nPropose-moi un plan concret sur 7 jours pour progresser, avec des exercices simples et "
            "des conseils spécifiques pour les examens officiels (Goethe / telc / TestDaF / DSH)."
        )

    context = {
        "profile": profile,
        "last_session": last_session,
        "preset": preset,
    }
    return render(request, "german/ai_coach.html", context)

@csrf_exempt
@login_required
def german_ai_coach_api(request):
    """
    Endpoint JSON pour le chat IA allemand.
    Reçoit : { "message": "...", "history": [ {role, content}, ... ] }
    Retourne : { "reply": "..." }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    if german_client is None:
        return JsonResponse(
            {
                "error": "API key manquante",
                "reply": "La clé OPENAI_API_KEY n'est pas configurée sur le serveur.",
            },
            status=500,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_message:
        return JsonResponse({"error": "Empty message"}, status=400)

    from .models import GermanTestSession

    profile = _get_or_create_profile(request.user)

    last_session = (
        GermanTestSession.objects
        .filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")
        .first()
    )

    # Contexte profil
    badges_text = ", ".join(profile.badges) if getattr(profile, "badges", None) else "aucun"
    profile_text = (
        f"Niveau interne: {profile.level}, XP: {profile.xp}, "
        f"Meilleur score: {profile.best_score:.1f}%, "
        f"Nombre de tests: {profile.total_tests}, "
        f"Badges: {badges_text}."
    )

    placement_text = ""
    if getattr(profile, "placement_level", None):
        placement_text = (
            f"Niveau conseillé par le test de niveau: {profile.placement_level}, "
            f"score test de niveau ≈ {getattr(profile, 'placement_score', 0):.1f} %."
        )

    last_test_text = ""
    if last_session:
        last_test_text = (
            f"Dernier test: {last_session.exam.title} "
            f"(type: {last_session.exam.exam_type}, niveau: {last_session.exam.level}), "
            f"score: {last_session.score:.1f}%."
        )

    system_prompt = (
        "Tu es un coach d'allemand personnalisé pour la plateforme Immigration97. "
        "Tu parles à un utilisateur francophone qui prépare des tests d'allemand officiels "
        "(Goethe, telc, TestDaF, DSH, tests d'intégration) pour l'immigration, les études ou le travail en Allemagne. "
        "Tu expliques de façon claire, bienveillante, concrète, avec beaucoup d'exemples simples. "
        "Tu peux proposer : mini-exercices (phrases à compléter, traduction, compréhension), "
        "stratégies pour Hören/Lesen/Schreiben/Sprechen, conseils de vocabulaire et de grammaire.\n\n"
        "Toujours :\n"
        "- t'adapter au niveau indiqué (A1–C2),\n"
        "- rappeler le lien avec les tests officiels (Goethe, telc, TestDaF, DSH),\n"
        "- terminer souvent par une petite action concrète que l'utilisateur peut faire tout de suite.\n\n"
        f"Profil utilisateur: {profile_text}\n"
        f"{placement_text}\n"
        f"Dernier test: {last_test_text}\n"
        "Si l'utilisateur est vague, aide-le à préciser son objectif (immigration, études, travail) "
        "et son niveau cible (ex: B1 pour visa, B2/C1 pour études)."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Historique précédent (pour garder une conversation fluide)
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Nouveau message utilisateur
    messages.append({"role": "user", "content": user_message})

    try:
        completion = german_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.4,
        )
        reply_text = completion.choices[0].message.content
    except OpenAIError as e:
        return JsonResponse(
            {
                "error": "IA error",
                "details": str(e),
                "reply": "Désolé, une erreur s'est produite côté IA (coach allemand).",
            },
            status=500,
        )

    return JsonResponse({"reply": reply_text})
