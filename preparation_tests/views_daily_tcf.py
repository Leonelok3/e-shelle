"""Daily practice with server-side answer keys and bounded AI correction."""
import logging
import json
import os
import tempfile
import time
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from canada_resume.ai_budget import ai_budget
from .services.daily_tcf import daily_session, grade_questions
from .models import TCFDailyProgress, UserSkillProgress

STATE_KEY = "tcf_daily_attempt"
logger = logging.getLogger(__name__)


def _target_level(user, skill):
    """Use the learner's measured TCF level, then their saved profile level."""
    valid = {"A1", "A2", "B1", "B2", "C1", "C2"}
    progress = UserSkillProgress.objects.filter(user=user, exam_code__iexact="tcf", skill=skill).values("current_level", "total_attempts").first()
    level = progress["current_level"] if progress and progress["total_attempts"] else None
    if level in valid:
        return level
    profile = getattr(user, "profile", None)
    level = getattr(profile, "level", "") if profile else ""
    return level if level in valid else "A1"


def _save_progress(user, daily, state):
    if not user.is_authenticated or not state.get("submitted"):
        return
    result = grade_questions(daily, state.get("answers", {})) if daily["skill"] in ("ce", "co") else {}
    coaching = state.get("coaching", {})
    TCFDailyProgress.objects.update_or_create(
        user=user, day=daily["date"],
        defaults={
            "skill": daily["skill"], "topic": daily["topic"], "task_number": daily.get("task_number"),
            "objective_correct": result.get("correct"), "objective_total": result.get("total"),
            "ai_score": coaching.get("score"), "word_count": state.get("word_count", 0),
            "elapsed_seconds": state.get("elapsed", 0), "overtime": state.get("overtime", False),
            "production": state.get("production", "")[:12000], "answers": state.get("answers", {}),
            "coaching": coaching,
        },
    )
    logger.info("tcf_daily_submission_saved skill=%s day=%s", daily["skill"], daily["key"])


def _load_saved_progress(user, daily):
    if not user.is_authenticated:
        return {}
    row = TCFDailyProgress.objects.filter(user=user, day=daily["date"]).first()
    if not row:
        return {}
    return {
        "day": daily["key"], "started": time.time() - row.elapsed_seconds, "submitted": True,
        "elapsed": row.elapsed_seconds, "overtime": row.overtime, "production": row.production,
        "word_count": row.word_count, "answers": row.answers, "coaching": row.coaching,
    }


def daily_progress_summary(user):
    """Recent completed sessions, summarized by skill for the TCF hub."""
    if not user.is_authenticated:
        return None
    rows = list(TCFDailyProgress.objects.filter(user=user, day__gte=timezone.localdate() - timedelta(days=27)).order_by("-day"))
    by_skill = []
    for skill, label in (("ce", "Compréhension écrite"), ("co", "Compréhension orale"), ("ee", "Expression écrite"), ("eo", "Expression orale")):
        items = [row for row in rows if row.skill == skill]
        scored = [row for row in items if row.ai_score is not None]
        objective = [row for row in items if row.objective_total]
        objective_pct = round(sum(row.objective_correct or 0 for row in objective) * 100 / sum(row.objective_total for row in objective)) if objective else None
        by_skill.append({"code": skill.upper(), "label": label, "count": len(items),
                         "average": round(sum(row.ai_score for row in scored) / len(scored)) if scored else objective_pct,
                         "score_label": "score moyen IA" if scored else ("réussite QCM" if objective_pct is not None else "pas encore de résultat")})
    days = {row.day for row in rows}
    streak = 0
    cursor = timezone.localdate()
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return {"sessions": len(rows), "streak": streak, "skills": by_skill, "recent": rows[:5]}


@never_cache
@require_http_methods(["GET", "POST"])
def daily_tcf(request):
    daily = daily_session()
    state = request.session.get(STATE_KEY, {})
    if state.get("day") != daily["key"]:
        state = _load_saved_progress(request.user, daily)
        if state:
            request.session[STATE_KEY] = state
    error = ""
    status = 200
    if request.method == "POST":
        action = request.POST.get("action")
        if request.POST.get("day") != daily["key"]:
            error, status = "La séance du jour a changé. Reviens à la page TCF pour ouvrir la nouvelle séance.", 409
        elif action == "start":
            if daily["skill"] == "co" and not daily["audio_ready"]:
                error, status = "L'audio du jour n'est pas encore disponible. Tu peux lire la leçon et travailler les autres compétences.", 409
            else:
                request.session[STATE_KEY] = {"day": daily["key"], "started": time.time(), "submitted": False}
                return redirect("preparation_tests:tcf_daily")
        elif action == "audio-play" and state.get("started") and not state.get("submitted") and daily["skill"] == "co":
            if state.get("audio_used"):
                return JsonResponse({"ok": False, "error": "Le document a déjà été lancé dans cette séance."}, status=409)
            state["audio_used"] = True
            request.session[STATE_KEY] = state
            return JsonResponse({"ok": True})
        elif action == "transcript" and state.get("submitted") and daily["skill"] == "eo":
            text = request.POST.get("production", "").strip()
            if len(text) > 12000:
                error, status = "La transcription dépasse 12 000 caractères.", 400
            else:
                state["production"] = text
                state["word_count"] = len(text.split())
                state.pop("coaching", None)
                request.session[STATE_KEY] = state
                _save_progress(request.user, daily, state)
                return redirect("preparation_tests:tcf_daily")
        elif action == "submit" and state.get("started") and not state.get("submitted"):
            state["elapsed"] = max(0, round(time.time() - state["started"]))
            state["overtime"] = state["elapsed"] > daily["duration"] + 2
            if daily["skill"] in ("ce", "co"):
                state["answers"] = {str(i): request.POST.get(f"answer_{i}", "") for i in range(len(daily["questions"]))}
            else:
                text = request.POST.get("production", "").strip()
                if len(text) > 12000:
                    error, status = "Ta réponse dépasse la longueur acceptée (12 000 caractères).", 400
                else:
                    state["production"] = text
                    state["word_count"] = len(text.split())
            if not error:
                state["submitted"] = True
                request.session[STATE_KEY] = state
                _save_progress(request.user, daily, state)
                days = request.session.get("tcf_daily_completed", [])
                request.session["tcf_daily_completed"] = (days + [daily["key"]] if daily["key"] not in days else days)[-31:]
                return redirect("preparation_tests:tcf_daily")
        else:
            error, status = "Commence la séance avant de rendre ta réponse. Une réponse déjà rendue reste accessible.", 400
    saved_days = (TCFDailyProgress.objects.filter(user=request.user, day__gte=timezone.localdate() - timedelta(days=30)).count()
                  if request.user.is_authenticated else len(request.session.get("tcf_daily_completed", [])))
    context = {"daily": daily, "attempt": state, "error": error,
               "active": bool(state.get("started") and not state.get("submitted")),
               "submitted": bool(state.get("submitted")),
               "completed_days": saved_days}
    if error and request.method == "POST":
        context["unsent_production"] = request.POST.get("production", "")[:12000]
    if state.get("started") and not state.get("submitted"):
        context["remaining"] = max(0, daily["duration"] - int(time.time() - state["started"]))
        # Never put keys or explanations in the exam HTML before submission.
        if "questions" in daily:
            daily = {**daily, "questions": [{"prompt": q["prompt"], "options": q["options"]} for q in daily["questions"]]}
            context["daily"] = daily
    if state.get("submitted") and daily["skill"] in ("ce", "co"):
        context["result"] = grade_questions(daily, state.get("answers", {}))
    return render(request, "preparation_tests/tcf_daily.html", context, status=status)


@login_required
@require_POST
def correct_daily_production(request):
    daily = daily_session()
    state = request.session.get(STATE_KEY, {})
    if daily["skill"] not in ("ee", "eo") or state.get("day") != daily["key"] or not state.get("submitted"):
        return JsonResponse({"ok": False, "error": "Rends d'abord ta production du jour."}, status=400)
    text = state.get("production", "")
    if len(text.split()) < 10:
        return JsonResponse({"ok": False, "error": "Écris au moins dix mots pour recevoir un retour utile."}, status=400)
    if state.get("coaching"):
        return JsonResponse({"ok": True, "result": state["coaching"]})
    return _evaluate_daily(request, daily, state, text)


@login_required
@require_POST
@ai_budget
def correct_daily_oral_audio(request):
    """Transcribe a learner's locally recorded answer, evaluate it, then discard the upload."""
    daily = daily_session()
    state = request.session.get(STATE_KEY, {})
    audio_file = request.FILES.get("audio")
    if daily["skill"] != "eo" or state.get("day") != daily["key"] or not state.get("submitted"):
        return JsonResponse({"ok": False, "error": "Rends d'abord ta séance orale."}, status=400)
    if not audio_file:
        return JsonResponse({"ok": False, "error": "Choisis un enregistrement avant de lancer l'analyse."}, status=400)
    if audio_file.size > 20 * 1024 * 1024:
        return JsonResponse({"ok": False, "error": "L'enregistrement dépasse la limite de 20 Mo."}, status=413)
    content_type = (audio_file.content_type or "").lower()
    if content_type and not content_type.startswith("audio/"):
        return JsonResponse({"ok": False, "error": "Le fichier sélectionné n'est pas reconnu comme un enregistrement audio."}, status=415)
    suffix = ".ogg" if "ogg" in content_type else ".mp4" if "mp4" in content_type else ".wav" if "wav" in content_type else ".webm"
    from ai_engine.services.eval_service import transcribe_audio
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp_path = temp.name
            for chunk in audio_file.chunks():
                temp.write(chunk)
        transcript = transcribe_audio(temp_path, language="fr").strip()[:12000]
    except Exception as exc:
        logger.warning("tcf_daily_ai_failure stage=transcription skill=eo day=%s error=%s", daily["key"], type(exc).__name__)
        return JsonResponse({"ok": False, "error": "Transcription indisponible. Tu peux saisir toi-même la transcription de ton oral."}, status=503)
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Impossible de supprimer le fichier audio temporaire TCF.")
    if not transcript:
        logger.warning("tcf_daily_ai_failure stage=empty_transcript skill=eo day=%s", daily["key"])
        return JsonResponse({"ok": False, "error": "Aucune transcription n'a pu être obtenue. Vérifie le son ou saisis ta transcription manuellement."}, status=503)
    if len(transcript.split()) < 10:
        return JsonResponse({"ok": False, "transcript": transcript, "error": "La transcription est trop courte pour fournir une correction utile. Vérifie le son ou complète-la dans le champ de transcription."}, status=422)
    state["production"] = transcript
    state["word_count"] = len(transcript.split())
    state["audio_transcribed"] = True
    state.pop("coaching", None)
    request.session[STATE_KEY] = state
    result = _evaluate_daily_core(request, daily, state, transcript)
    payload = json.loads(result.content.decode("utf-8"))
    payload["transcript"] = transcript
    return JsonResponse(payload, status=result.status_code)


@ai_budget
def _evaluate_daily(request, daily, state, text):
    return _evaluate_daily_core(request, daily, state, text)


def _evaluate_daily_core(request, daily, state, text):
    from .services.learning_coach import evaluate_production
    try:
        expected_points = []
        if daily["skill"] == "ee":
            expected_points = [f"Respecter la limite de {daily['word_min']} à {daily['word_max']} mots.",
                               "Traiter chacun des éléments demandés par la consigne."]
        level = _target_level(request.user, daily["skill"])
        result = evaluate_production(text, daily["question"], daily["format_label"] + "\n" + daily.get("document", ""),
                                     level, daily["skill"], context={"exam": "tcf", "target_level": level,
                                                                    "expected_points": expected_points})
        if daily["skill"] == "ee" and not daily["word_min"] <= state.get("word_count", len(text.split())) <= daily["word_max"]:
            result.setdefault("coaching", {})["length_guidance"] = (
                f"Ta réponse compte {state.get('word_count', len(text.split()))} mots ; la consigne en demande "
                f"{daily['word_min']} à {daily['word_max']}. La correction reste disponible pour apprendre, "
                "mais la note de respect du format est moins représentative tant que cette limite n'est pas respectée."
            )
    except Exception as exc:
        logger.warning("tcf_daily_ai_failure stage=evaluation skill=%s day=%s error=%s", daily["skill"], daily["key"], type(exc).__name__)
        return JsonResponse({"ok": False, "error": "La correction IA est momentanément indisponible. Ta réponse est conservée ; tu peux réessayer."}, status=503)
    state["coaching"] = result
    request.session[STATE_KEY] = state
    _save_progress(request.user, daily, state)
    return JsonResponse({"ok": True, "result": result})
