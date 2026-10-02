"""Daily practice with server-side answer keys and bounded AI correction."""
import time
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from canada_resume.ai_budget import ai_budget
from .services.daily_tcf import daily_session, grade_questions

STATE_KEY = "tcf_daily_attempt"


@never_cache
@require_http_methods(["GET", "POST"])
def daily_tcf(request):
    daily = daily_session()
    state = request.session.get(STATE_KEY, {})
    if state.get("day") != daily["key"]:
        state = {}
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
                days = request.session.get("tcf_daily_completed", [])
                request.session["tcf_daily_completed"] = (days + [daily["key"]] if daily["key"] not in days else days)[-31:]
                return redirect("preparation_tests:tcf_daily")
        else:
            error, status = "Commence la séance avant de rendre ta réponse. Une réponse déjà rendue reste accessible.", 400
    context = {"daily": daily, "attempt": state, "error": error,
               "active": bool(state.get("started") and not state.get("submitted")),
               "submitted": bool(state.get("submitted")),
               "completed_days": len(request.session.get("tcf_daily_completed", []))}
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


@ai_budget
def _evaluate_daily(request, daily, state, text):
    from .services.learning_coach import evaluate_production
    try:
        result = evaluate_production(text, daily["question"], daily["format_label"] + "\n" + daily.get("document", ""),
                                     "B2", daily["skill"], context={"exam": "tcf"})
    except Exception:
        return JsonResponse({"ok": False, "error": "La correction IA est momentanément indisponible. Ta réponse est conservée ; tu peux réessayer."}, status=503)
    state["coaching"] = result
    request.session[STATE_KEY] = state
    return JsonResponse({"ok": True, "result": result})
