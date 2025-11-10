# preparation_tests/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Exam, ExamSection, Question, Choice, Session, Attempt, Answer
from django.urls import reverse


# ✅ PAGE D’ACCUEIL DU MODULE (celle que tu utilises déjà)
def home(request):
    return render(request, "preparation_tests/home.html")


# ✅ Utilitaire : récupérer la prochaine question non répondue
def _next_unanswered_question(attempt: Attempt) -> Question | None:
    answered_ids = set(attempt.answers.values_list("question_id", flat=True))
    return attempt.section.questions.exclude(id__in=answered_ids).order_by("id").first()


# ✅ Liste des examens
def exam_list(request: HttpRequest) -> HttpResponse:
    exams = Exam.objects.all().order_by("language", "name")
    return render(request, "preparation_tests/exam_list.html", {"exams": exams})


# ✅ Détail d’un examen : sections
def exam_detail(request: HttpRequest, exam_code: str) -> HttpResponse:
    exam = get_object_or_404(Exam, code=exam_code)
    sections = exam.sections.all()
    return render(request, "preparation_tests/exam_detail.html", {"exam": exam, "sections": sections})


# ✅ Démarrer une session
@login_required
def start_session(request: HttpRequest, exam_code: str) -> HttpResponse:
    exam = get_object_or_404(Exam, code=exam_code)

    session = Session.objects.create(user=request.user, exam=exam, mode="practice")
    first_section = exam.sections.order_by("order").first()

    if not first_section:
        messages.error(request, "Aucune section définie pour cet examen.")
        return redirect("preparation_tests:exam_detail", exam_code=exam.code)

    attempt = Attempt.objects.create(session=session, section=first_section)
    return redirect("preparation_tests:take_section", attempt_id=attempt.id)


# ✅ Prendre une section : question par question
@login_required
def take_section(request: HttpRequest, attempt_id: int) -> HttpResponse:
    attempt = get_object_or_404(Attempt, id=attempt_id, session__user=request.user)
    section = attempt.section

    q = _next_unanswered_question(attempt)
    if not q:
        # → Section terminée
        total = section.questions.count()
        correct = attempt.answers.filter(is_correct=True).count()

        attempt.total_items = total
        attempt.raw_score = float(correct)
        attempt.ended_at = timezone.now()
        attempt.save()

        attempt.session.completed_at = timezone.now()
        attempt.session.save()

        return redirect("preparation_tests:session_result", session_id=attempt.session.id)

    # → Affichage question
    choices = q.choices.all() if q.subtype == "mcq" else None
    return render(
        request,
        "preparation_tests/question.html",
        {
            "attempt": attempt,
            "section": section,
            "question": q,
            "choices": choices,
            "duration_sec": section.duration_sec,
        },
    )


# ✅ Soumettre réponse
@login_required
def submit_answer(request: HttpRequest, attempt_id: int, question_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404()

    attempt = get_object_or_404(Attempt, id=attempt_id, session__user=request.user)
    question = get_object_or_404(Question, id=question_id, section=attempt.section)

    is_correct = False
    payload = {}

    if question.subtype == "mcq":
        choice_id = request.POST.get("choice")
        if not choice_id:
            messages.error(request, "Veuillez sélectionner une réponse.")
            return redirect("preparation_tests:take_section", attempt_id=attempt.id)

        try:
            choice = Choice.objects.get(id=int(choice_id), question=question)
        except:
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
        is_correct = False  # correction avancée sera ajoutée plus tard

    Answer.objects.create(
        attempt=attempt,
        question=question,
        payload=payload,
        is_correct=is_correct,
    )

    return redirect("preparation_tests:take_section", attempt_id=attempt.id)


# ✅ Résultat final
@login_required
def session_result(request: HttpRequest, session_id: int) -> HttpResponse:
    session = get_object_or_404(Session, id=session_id, user=request.user)
    attempts = session.attempts.select_related("section").all()

    total_items = sum(a.total_items for a in attempts)
    total_correct = sum(int(a.raw_score) for a in attempts)

    return render(
        request,
        "preparation_tests/result.html",
        {
            "session": session,
            "attempts": attempts,
            "total_items": total_items,
            "total_correct": total_correct,
        },
    )

# fonction page examen de francais 
def french_exams(request):
    return render(request, "preparation_tests/french_exams.html")


def tef_hub(request):
    return render(request, "preparation_tests/fr_tef_hub.html")

def tcf_hub(request):
    return render(request, "preparation_tests/fr_tcf_hub.html")

def delf_hub(request):
    return render(request, "preparation_tests/fr_delf_hub.html")


# fonction page examen d'anglais
def english_exams(request):
    return render(request, "preparation_tests/english_exams.html")


# fonction page examens allemand
def german_exams(request):
    return render(request, "preparation_tests/german_exams.html")

