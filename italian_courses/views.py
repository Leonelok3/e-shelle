# italian_courses/views.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    CourseCategory,
    Lesson,
    LessonProgress,
    Quiz,
    Question,
    Choice,
)


def category_list(request: HttpRequest) -> HttpResponse:
    categories = CourseCategory.objects.filter(is_active=True).order_by("order", "name")
    return render(request, "italian_courses/category_list.html", {"categories": categories})


def lesson_list(request: HttpRequest, category_slug: str) -> HttpResponse:
    category = get_object_or_404(CourseCategory, slug=category_slug, is_active=True)

    # ✅ IMPORTANT: tri par "order" (champ réel), pas "order_index"
    lessons_qs = Lesson.objects.filter(category=category, is_published=True).order_by("order", "title")

    progress_by_lesson_id = {}
    if request.user.is_authenticated:
        progress_qs = LessonProgress.objects.filter(user=request.user, lesson__in=lessons_qs)
        progress_by_lesson_id = {p.lesson_id: p for p in progress_qs}

    return render(
        request,
        "italian_courses/lesson_list.html",
        {
            "category": category,
            "lessons": lessons_qs,
            "progress_by_lesson_id": progress_by_lesson_id,
        },
    )


def lesson_detail(request: HttpRequest, category_slug: str, lesson_slug: str) -> HttpResponse:
    category = get_object_or_404(CourseCategory, slug=category_slug, is_active=True)
    lesson = get_object_or_404(Lesson, category=category, slug=lesson_slug, is_published=True)

    quizzes = Quiz.objects.filter(lesson=lesson, is_active=True).order_by("order", "title")

    progress = None
    if request.user.is_authenticated:
        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={"progress_percent": 0.00, "completed": False},
        )

    return render(
        request,
        "italian_courses/lesson_detail.html",
        {
            "category": category,
            "lesson": lesson,
            "quizzes": quizzes,
            "progress": progress,
        },
    )


@login_required
def mark_lesson_completed(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Pour matcher ton urls.py actuel qui appelle:
    path("lecon/<slug:slug>/terminer/", views.mark_lesson_completed, ...)
    """
    # ⚠️ Ici on suppose que slug identifie une Lesson de façon unique.
    # Si ce n'est pas le cas chez toi, on corrigera urls.py pour inclure category_slug + lesson_slug.
    lesson = get_object_or_404(Lesson, slug=slug, is_published=True)

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={"progress_percent": 0.00, "completed": False},
    )
    progress.mark_completed()
    progress.save()

    messages.success(request, "Leçon marquée comme terminée ✅")

    # Si tu as une route lesson_detail basée sur category+slug, on y retourne
    try:
        return redirect("italian_courses:lesson_detail", category_slug=lesson.category.slug, lesson_slug=lesson.slug)
    except Exception:
        # fallback si ton urls.py n'a pas ce pattern
        return redirect("italian_courses:lesson_list", category_slug=lesson.category.slug)


@login_required
def quiz_take(request: HttpRequest, quiz_id: int) -> HttpResponse:
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)

    questions = (
        Question.objects.filter(quiz=quiz)
        .prefetch_related(Prefetch("choices", queryset=Choice.objects.order_by("order", "id")))
        .order_by("order", "id")
    )

    if request.method == "POST":
        total = 0
        correct = 0
        answers = {}

        for q in questions:
            total += 1
            choice_id = request.POST.get(f"q_{q.id}")
            if not choice_id:
                answers[q.id] = None
                continue

            try:
                selected = Choice.objects.get(id=int(choice_id), question=q)
            except (ValueError, Choice.DoesNotExist):
                answers[q.id] = None
                continue

            answers[q.id] = selected.id
            if selected.is_correct:
                correct += 1

        request.session[f"quiz_{quiz.id}_result"] = {
            "total": total,
            "correct": correct,
            "answers": answers,
        }
        return redirect("italian_courses:quiz_result", quiz_id=quiz.id)

    return render(
        request,
        "italian_courses/quiz_take.html",
        {
            "quiz": quiz,
            "lesson": quiz.lesson,
            "category": quiz.lesson.category,
            "questions": questions,
        },
    )


@login_required
def quiz_result(request: HttpRequest, quiz_id: int) -> HttpResponse:
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)

    result = request.session.get(f"quiz_{quiz.id}_result")
    if not result:
        return redirect("italian_courses:quiz_take", quiz_id=quiz.id)

    total = int(result.get("total", 0))
    correct = int(result.get("correct", 0))
    score_percent = (correct / total * 100.0) if total > 0 else 0.0

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=quiz.lesson,
        defaults={"progress_percent": 0.00, "completed": False},
    )

    if score_percent >= 80.0:
        progress.mark_completed()
        progress.save()
    else:
        new_value = max(float(progress.progress_percent), min(score_percent, 99.99))
        progress.progress_percent = new_value
        progress.save(update_fields=["progress_percent", "last_accessed_at"])

    return render(
        request,
        "italian_courses/quiz_result.html",
        {
            "quiz": quiz,
            "lesson": quiz.lesson,
            "category": quiz.lesson.category,
            "total": total,
            "correct": correct,
            "score_percent": round(score_percent, 2),
            "progress": progress,
        },
    )
