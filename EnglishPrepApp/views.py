import json
from django.conf import settings

from openai import OpenAI, OpenAIError

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max, Avg   # 👈 AJOUT ICI


from .models import (
    EnglishTest,
    EnglishQuestion,
    UserTestSession,
    UserAnswer,
    EnglishUserProfile,
    EnglishLesson,
    LEVEL_THRESHOLDS,
)

# =============================
# CLIENT OPENAI - COACH IA
# =============================
OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", None)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# =========================
#  UTILITAIRES
# =========================

def _get_or_create_profile(user) -> EnglishUserProfile:
    """
    Récupère le profil anglais ou le crée s'il n'existe pas.
    """
    profile, _ = EnglishUserProfile.objects.get_or_create(user=user)
    return profile


def _compute_exam_stats(user):
    """
    Stats par type d'examen (GENERAL, IELTS, TOEFL, TOEIC) :
    - nombre de tests
    - meilleur score
    - score moyen
    """
    qs = (
        UserTestSession.objects
        .filter(user=user, score__isnull=False)
        .select_related("test")
    )

    stats = {}

    for exam_code, exam_label in EnglishTest.EXAM_CHOICES:
        sub = qs.filter(test__exam_type=exam_code)
        if not sub.exists():
            continue

        agg = sub.aggregate(
            best=Max("score"),
            avg=Avg("score"),
        )

        stats[exam_code] = {
            "label": exam_label,
            "count": sub.count(),
            "best": round(agg["best"] or 0.0, 1),
            "avg": round(agg["avg"] or 0.0, 1),
        }

    return stats


# =========================
#  PROFIL / PROGRESSION ANGLAIS
# =========================

@login_required
def english_profile(request):
    """
    Page Profil / progression anglais :
    - XP, niveau, progression vers le prochain niveau
    - Badges
    - Stats par type d'examen
    - Derniers tests
    - Recommandation dynamique
    - Prompt pré-rempli pour le coach IA
    """
    profile = _get_or_create_profile(request.user)

    # Dernières sessions (timeline)
    sessions = (
        UserTestSession.objects
        .filter(user=request.user)
        .select_related("test")
        .order_by("-started_at")[:10]
    )

    # Stats par type d'examen
    exam_stats = _compute_exam_stats(request.user)

    # ---------- Progression niveau ----------
    xp = profile.xp or 0
    current_level = profile.level or 1
    thresholds = LEVEL_THRESHOLDS  # ex: [(1, 0), (2, 100), ...]

    current_min_xp = 0
    next_level = current_level + 1
    next_level_xp = None

    for lvl, threshold in thresholds:
        if lvl == current_level:
            current_min_xp = threshold
        if lvl == current_level + 1:
            next_level_xp = threshold

    if next_level_xp is None:
        # au-delà du dernier palier : on continue par blocs de 400 XP
        last_level, last_threshold = thresholds[-1]
        if current_level <= last_level:
            current_min_xp = dict(thresholds).get(current_level, last_threshold)
            next_level_xp = last_threshold + 400
        else:
            current_min_xp = thresholds[-1][1] + 400 * (current_level - last_level - 1)
            next_level_xp = current_min_xp + 400

    xp_in_level = max(0, xp - current_min_xp)
    xp_needed = max(1, next_level_xp - current_min_xp)
    level_progress_pct = int(round(100 * min(xp_in_level / xp_needed, 1)))

    # ---------- Recommandation dynamique ----------
    exam_with_lowest_avg = None
    if exam_stats:
        exam_with_lowest_avg = min(
            exam_stats.values(),
            key=lambda s: s["avg"]
        )

    if profile.total_tests == 0:
        next_step = (
            "Commence par passer un premier test d’anglais général niveau B1 "
            "pour établir ton niveau de base."
        )
    elif profile.best_score < 60:
        if exam_with_lowest_avg:
            next_step = (
                f"Ton point faible actuel semble être {exam_with_lowest_avg['label']} "
                f"(moyenne ≈ {exam_with_lowest_avg['avg']} %). "
                "Refais un test dans cette catégorie et concentre-toi sur la compréhension des corrections."
            )
        else:
            next_step = (
                "Tu es en dessous de 60 % en moyenne. "
                "Refais un test que tu as déjà passé et essaie de gagner au moins +10 points."
            )
    elif profile.best_score < 80:
        if exam_with_lowest_avg:
            next_step = (
                f"Tu as déjà une base correcte. Travaille maintenant {exam_with_lowest_avg['label']} "
                "pour stabiliser tes scores au-dessus de 75 %."
            )
        else:
            next_step = (
                "Continue à enchaîner les tests réguliers et vise des scores stables au-dessus de 75 %."
            )
    else:
        next_step = (
            "Ton niveau global est déjà solide. Enchaîne les tests complets de type IELTS / TOEFL / TOEIC "
            "pour te rapprocher de ton score cible officiel."
        )

    # ---------- Prompt pré-rempli pour le coach IA ----------
    coach_preset = (
        "Analyse mon profil d'anglais sur Immigration97 et propose-moi un plan concret :\n"
        f"- Niveau actuel: {profile.level}\n"
        f"- XP: {profile.xp}\n"
        f"- Meilleur score: {profile.best_score:.1f} %\n"
        f"- Nombre de tests: {profile.total_tests}\n"
    )
    if exam_with_lowest_avg:
        coach_preset += (
            f"- Point faible probable: {exam_with_lowest_avg['label']} "
            f"(moyenne ≈ {exam_with_lowest_avg['avg']} %)\n"
        )
    coach_preset += (
        "\nDonne-moi :\n"
        "1) Un résumé rapide de mon niveau.\n"
        "2) Les 2–3 priorités à travailler.\n"
        "3) Un mini-plan sur 7 jours adapté à mon objectif (immigration, études ou travail)."
    )

    context = {
        "profile": profile,
        "sessions": sessions,
        "exam_stats": exam_stats,
        "level_progress_pct": level_progress_pct,
        "next_level": next_level,
        "current_min_xp": current_min_xp,
        "next_level_xp": next_level_xp,
        "next_step": next_step,
        "coach_preset": coach_preset,
    }
    # 🔁 Template profil : à créer -> english/profile.html
    return render(request, "english/profile.html", context)


# =========================
#  DASHBOARD
# =========================

@login_required
def dashboard(request):
    """
    Tableau de bord principal anglais.
    """
    profile = _get_or_create_profile(request.user)

    last_sessions = (
        UserTestSession.objects
        .filter(user=request.user)
        .select_related("test")
        .order_by("-started_at")[:5]
    )

    answers = (
        UserAnswer.objects
        .filter(session__user=request.user)
        .select_related("question")
    )

    skill_stats = {
        "READING": {"label": "Reading", "total": 0, "correct": 0},
        "USE_OF_ENGLISH": {
            "label": "Grammaire / Vocabulaire",
            "total": 0,
            "correct": 0,
        },
    }

    for ans in answers:
        skill = ans.question.skill
        if skill in skill_stats:
            skill_stats[skill]["total"] += 1
            if ans.is_correct:
                skill_stats[skill]["correct"] += 1

    for data in skill_stats.values():
        total = data["total"]
        if total:
            data["pct"] = int(round(100 * data["correct"] / total))
        else:
            data["pct"] = 0

    context = {
        "profile": profile,
        "last_sessions": last_sessions,
        "skill_stats": skill_stats,
    }
    return render(request, "english/dashboard.html", context)


# =========================
#  LISTE DES TESTS
# =========================

@login_required
def test_list(request):
    tests = (
        EnglishTest.objects
        .filter(is_active=True)
        .order_by("exam_type", "level", "name")
    )
    return render(request, "english/test_list.html", {"tests": tests})


# =========================
#  PASSER UN TEST
# =========================

@login_required
def take_test(request, test_id):
    """
    Page de passation du test :
    - Affiche toutes les questions
    - Gère l'enregistrement des réponses
    - Timer côté front (durée = test.duration_minutes)
    """
    test = get_object_or_404(EnglishTest, pk=test_id, is_active=True)

    session, _ = UserTestSession.objects.get_or_create(
        user=request.user,
        test=test,
    )

    questions = (
        EnglishQuestion.objects
        .filter(test=test)
        .order_by("id")
    )

    if request.method == "POST":
        correct_count = 0
        total_questions = questions.count()

        # Nettoyage des anciennes réponses
        UserAnswer.objects.filter(session=session).delete()

        for q in questions:
            field_name = f"question_{q.id}"
            selected_option = request.POST.get(field_name)
            if not selected_option:
                continue

            is_correct = (selected_option == q.correct_option)
            if is_correct:
                correct_count += 1

            UserAnswer.objects.create(
                session=session,
                question=q,
                selected_option=selected_option,
                is_correct=is_correct,
            )

        score_percent = (
            round(correct_count * 100.0 / total_questions, 2)
            if total_questions > 0 else 0.0
        )

        session.score = score_percent
        session.total_questions = total_questions
        session.correct_answers = correct_count
        session.finished_at = timezone.now()

        # ✅ AJOUT CHRONO (SAFE)
        duration = request.POST.get("duration_seconds")
        try:
            session.duration_seconds = int(duration)
        except (TypeError, ValueError):
            session.duration_seconds = 0

        session.save()

        # Gamification
        profile = _get_or_create_profile(request.user)
        gained_xp = profile.add_result(
            score_percent,
            total_questions,
            exam_type=test.exam_type,
        )
        request.session["last_english_xp_gain"] = gained_xp

        return redirect("englishprep:test_result", test_id=test.id)

    context = {
        "test": test,
        "session": session,
        "questions": questions,
        "duration_minutes": test.duration_minutes or 20,
    }
    return render(request, "english/take_test.html", context)



# =========================
#  RÉSULTAT D’UN TEST
# =========================

@login_required
def test_result(request, test_id):
    test = get_object_or_404(EnglishTest, id=test_id)

    session = (
        UserTestSession.objects
        .filter(user=request.user, test=test)
        .order_by("-started_at")
        .first()
    )
    if not session:
        messages.info(request, "Tu n'as pas encore passé ce test.")
        return redirect("englishprep:test_list")

    answers = session.answers.select_related("question")
    total = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    incorrect_answers = total - correct_answers

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

    # XP gagnée sur ce test (si dispo)
    xp_gain = request.session.pop("last_english_xp_gain", None)

    skill_stats = {}
    for ans in answers:
        skill = ans.question.skill
        stat = skill_stats.setdefault(skill, {"total": 0, "correct": 0})
        stat["total"] += 1
        if ans.is_correct:
            stat["correct"] += 1

    for stat in skill_stats.values():
        if stat["total"]:
            stat["pct"] = int(round(100 * stat["correct"] / stat["total"]))
        else:
            stat["pct"] = 0

    context = {
        "test": test,
        "session": session,
        "answers": answers,
        "total": total,
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers,
        "score": score or 0,
        "profile": profile,
        "skill_stats": skill_stats,
        "xp_gain": xp_gain,
    }
    return render(request, "english/test_result.html", context)


# =========================
#  HISTORIQUE DES TESTS
# =========================

@login_required
def test_history(request):
    profile = _get_or_create_profile(request.user)
    sessions = (
        UserTestSession.objects
        .filter(user=request.user)
        .select_related("test")
        .order_by("-started_at")
    )

    context = {
        "profile": profile,
        "sessions": sessions,
    }
    return render(request, "english/test_history.html", context)


# =========================
#  RÉVISION DES ERREURS
# =========================

@login_required
def review_incorrect(request, test_id):
    """
    Page spéciale pour revoir uniquement les questions ratées
    du dernier passage de ce test.
    """
    test = get_object_or_404(EnglishTest, id=test_id)

    session = (
        UserTestSession.objects
        .filter(user=request.user, test=test)
        .order_by("-started_at")
        .first()
    )
    if not session:
        messages.info(request, "Tu n'as pas encore passé ce test.")
        return redirect("englishprep:test_list")

    answers = session.answers.select_related("question")
    incorrect_answers = answers.filter(is_correct=False)
    total = answers.count()
    incorrect_count = incorrect_answers.count()

    if incorrect_count == 0:
        messages.success(
            request,
            "Tu n'as aucune erreur sur ce test. Félicitations ! 🎉",
        )
        return redirect("englishprep:test_result", test_id=test.id)

    context = {
        "test": test,
        "session": session,
        "incorrect_answers": incorrect_answers,
        "incorrect_count": incorrect_count,
        "total": total,
    }
    return render(request, "english/review_incorrect.html", context)


# =========================================================
# 📈 ANALYSE DES COMPÉTENCES PAR SESSION
# =========================================================

@login_required
def test_skill_analysis(request, session_id):
    """
    Analyse des compétences pour UNE session :
    - stats par skill (READING, USE_OF_ENGLISH, etc.)
    - structure adaptée au template english/skill_analysis.html
    """
    session = get_object_or_404(UserTestSession, id=session_id, user=request.user)

    answers = (
        UserAnswer.objects
        .filter(session=session)
        .select_related("question")
    )

    if not answers.exists():
        messages.info(
            request,
            "Aucune réponse enregistrée pour cette session. "
            "Lance un nouveau test pour générer des statistiques."
        )
        return redirect("englishprep:dashboard")

    skill_stats = {}
    label_map = dict(EnglishQuestion.SKILL_CHOICES)

    for ans in answers:
        skill = ans.question.skill
        data = skill_stats.setdefault(skill, {"total": 0, "correct": 0})
        data["total"] += 1
        if ans.is_correct:
            data["correct"] += 1

    for code, data in skill_stats.items():
        total = data["total"]
        correct = data["correct"]
        pct = round((correct / total) * 100, 1) if total else 0.0
        data["pct"] = pct
        data["label"] = label_map.get(code, code.title())

    global_total = sum(d["total"] for d in skill_stats.values())
    global_correct = sum(d["correct"] for d in skill_stats.values())
    global_pct = round((global_correct / global_total) * 100, 1) if global_total else 0.0

    profile = _get_or_create_profile(request.user)

    context = {
        "session": session,
        "skill_stats": skill_stats,
        "global_total": global_total,
        "global_correct": global_correct,
        "global_pct": global_pct,
        "profile": profile,
    }
    return render(request, "english/skill_analysis.html", context)


# ---------------------------------------------------------
# HUB IELTS / TOEFL / TOEIC basé sur EnglishTest
# ---------------------------------------------------------

@login_required
def english_exam_hub(request):
    """
    Hub marketing IELTS / TOEFL / TOEIC + liens rapides vers les tests.
    Utilise EnglishTest.exam_type (GENERAL / IELTS / TOEFL / TOEIC).
    """
    profile = _get_or_create_profile(request.user)

    total_sessions = UserTestSession.objects.filter(user=request.user).count()
    last_sessions = (
        UserTestSession.objects
        .filter(user=request.user)
        .select_related("test")
        .order_by("-started_at")[:5]
    )

    ielts_tests = EnglishTest.objects.filter(is_active=True, exam_type="IELTS")
    toefl_tests = EnglishTest.objects.filter(is_active=True, exam_type="TOEFL")
    toeic_tests = EnglishTest.objects.filter(is_active=True, exam_type="TOEIC")
    general_tests = EnglishTest.objects.filter(is_active=True, exam_type="GENERAL")

    context = {
        "profile": profile,
        "total_sessions": total_sessions,
        "last_sessions": last_sessions,
        "ielts_exams": ielts_tests,
        "toefl_exams": toefl_tests,
        "toeic_exams": toeic_tests,
        "general_exams": general_tests,
    }
    return render(request, "english/english_exam_hub.html", context)


# ---------------------------------------------------------
# COURS & EXERCICES / LEARNING PATH
# ---------------------------------------------------------

@login_required
def exam_learning_path(request, test_id):
    """
    Page 'Cours & exercices' pour un examen donné.
    Regroupe les leçons par compétence (CO / CE / EO / EE / Grammaire).
    """
    test = get_object_or_404(EnglishTest, pk=test_id)
    lessons = (
        EnglishLesson.objects.filter(test=test)
        .prefetch_related("exercises")
        .order_by("skill", "order", "title")
    )

    context = {
        "test": test,
        "lessons": lessons,
    }
    return render(request, "english/exam_learning_path.html", context)


# =========================
#  COACH IA (chat JS)
# =========================

@login_required
def ai_coach_page(request):
    """
    Page principale du coach IA.
    Il récupère le profil d'anglais + le dernier test pour personnaliser le coaching.
    Accepte un paramètre GET ?preset= pour pré-remplir la zone de texte.
    """
    profile = getattr(request.user, "english_profile", None)

    last_session = (
        UserTestSession.objects
        .filter(user=request.user)
        .select_related("test")
        .order_by("-started_at")
        .first()
    )

    preset = (request.GET.get("preset") or "").strip()

    context = {
        "profile": profile,
        "last_session": last_session,
        "preset": preset,
    }
    return render(request, "EnglishPrepApp/ai_coach.html", context)


@csrf_exempt
@login_required
def ai_coach_api(request):
    """
    Endpoint JSON pour le chat IA.
    Reçoit : { "message": "...", "history": [ {role, content}, ... ] }
    Retourne : { "reply": "..." }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    if client is None:
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

    profile = getattr(request.user, "english_profile", None)
    last_session = (
        UserTestSession.objects
        .filter(user=request.user)
        .select_related("test")
        .order_by("-started_at")
        .first()
    )

    profile_text = ""
    if profile:
        profile_text = (
            f"Niveau actuel: {profile.level}, XP: {profile.xp}, "
            f"Meilleur score: {profile.best_score}%, "
            f"Nombre de tests: {profile.total_tests}, "
            f"Badges: {', '.join(profile.badges) if profile.badges else 'aucun'}."
        )

    last_test_text = ""
    if last_session:
        last_test_text = (
            f"Dernier test: {last_session.test.name} "
            f"(type: {last_session.test.exam_type}, niveau: {last_session.test.level}), "
            f"score: {last_session.score}%."
        )

    system_prompt = (
        "Tu es un coach d'anglais personnalisé pour la plateforme Immigration97. "
        "Tu parles à un utilisateur francophone qui prépare des tests d'anglais "
        "(IELTS, TOEFL, TOEIC ou tests généraux) pour l'immigration, les études ou le travail. "
        "Tu expliques de façon claire, bienveillante, concrète, avec beaucoup d'exemples simples. "
        "Tu peux proposer : mini-exercices, phrases à compléter, correction d'erreurs, stratégies d'examen. "
        "Toujours :\n"
        "- t'adapter au niveau indiqué,\n"
        "- rappeler le lien avec les tests officiels,\n"
        "- terminer souvent par une petite action concrète que l'utilisateur peut faire tout de suite.\n\n"
        f"Profil utilisateur: {profile_text}\n"
        f"Dernier test: {last_test_text}\n"
        "Si l'utilisateur demande quelque chose de vague, aide-le à clarifier son objectif "
        "(immigration, études, travail)."
    )

    messages = [{"role": "system", "content": system_prompt}]

    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
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
                "reply": "Désolé, une erreur s'est produite côté IA.",
            },
            status=500,
        )

    return JsonResponse({"reply": reply_text})
