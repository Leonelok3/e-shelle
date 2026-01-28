# italian_courses/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import CourseCategory, Lesson, LessonProgress, Quiz


def category_list(request):
    categories = CourseCategory.objects.filter(is_active=True).order_by("order", "name")
    return render(
        request,
        "italian_courses/category_list.html",
        {"categories": categories},
    )


def lesson_list(request, category_slug):
    category = get_object_or_404(CourseCategory, slug=category_slug, is_active=True)

    qs = Lesson.objects.filter(category=category, is_published=True)

    # ✅ Important : dans ton modèle c’est "order" (pas order_index)
    lessons = list(qs.order_by("order", "title"))

    progress_by_lesson_id = {}
    if request.user.is_authenticated:
        progress_qs = LessonProgress.objects.filter(user=request.user, lesson__in=lessons)
        progress_by_lesson_id = {p.lesson_id: p for p in progress_qs}

    return render(
        request,
        "italian_courses/lesson_list.html",
        {
            "category": category,
            "lessons": lessons,
            "progress_by_lesson_id": progress_by_lesson_id,
        },
    )


def lesson_detail(request, category_slug, lesson_slug):
    category = get_object_or_404(CourseCategory, slug=category_slug, is_active=True)
    lesson = get_object_or_404(Lesson, category=category, slug=lesson_slug, is_published=True)

    quizzes = Quiz.objects.filter(lesson=lesson, is_active=True).order_by("order", "id")

    progress = None
    if request.user.is_authenticated:
        progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

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
def mark_lesson_completed(request, category_slug, slug):
    """
    ✅ Correction : on récupère la leçon par (category + slug).
    Sinon, si 2 catégories ont la même leçon slug, ça plante.
    """
    category = get_object_or_404(CourseCategory, slug=category_slug, is_active=True)
    lesson = get_object_or_404(Lesson, category=category, slug=slug, is_published=True)

    LessonProgress.objects.update_or_create(
        user=request.user,
        lesson=lesson,
        defaults={"completed": True},
    )

    return redirect(
        reverse(
            "italian_courses:lesson_detail",
            kwargs={"category_slug": category.slug, "lesson_slug": lesson.slug},
        )
    )


def quiz_take(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    questions = quiz.questions.all().order_by("order", "id")

    if request.method == "POST":
        score = 0
        total = questions.count()

        for q in questions:
            chosen_id = request.POST.get(f"q_{q.id}")
            if not chosen_id:
                continue
            # Choice.correct = bool (champ "is_correct" chez toi -> adapte si besoin)
            try:
                choice = q.choices.get(id=int(chosen_id))
                if getattr(choice, "is_correct", False):
                    score += 1
            except Exception:
                pass

        if request.user.is_authenticated:
            LessonProgress.objects.update_or_create(
                user=request.user,
                lesson=quiz.lesson,
                defaults={"completed": True},
            )

        request.session[f"quiz_score_{quiz.id}"] = score
        request.session[f"quiz_total_{quiz.id}"] = total

        return redirect("italian_courses:quiz_result", quiz_id=quiz.id)

    return render(
        request,
        "italian_courses/quiz_take.html",
        {"quiz": quiz, "questions": questions},
    )


def quiz_result(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    score = request.session.get(f"quiz_score_{quiz.id}", 0)
    total = request.session.get(f"quiz_total_{quiz.id}", 0)

    return render(
        request,
        "italian_courses/quiz_result.html",
        {"quiz": quiz, "score": score, "total": total},
    )
