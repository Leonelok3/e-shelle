# italian_courses/urls.py
from django.urls import path

from . import views

app_name = "italian_courses"

urlpatterns = [
    # /italien/
    path("", views.category_list, name="category_list"),

    # /italien/cours/<category_slug>/
    path("cours/<slug:category_slug>/", views.lesson_list, name="lesson_list"),

    # /italien/cours/<category_slug>/<lesson_slug>/
    path(
        "cours/<slug:category_slug>/<slug:lesson_slug>/",
        views.lesson_detail,
        name="lesson_detail",
    ),

    # Quiz
    path("quiz/<int:quiz_id>/", views.quiz_take, name="quiz_take"),
    path("quiz/<int:quiz_id>/resultat/", views.quiz_result, name="quiz_result"),

    # Compat (si ton ancien template/urls l'utilise encore)
    path("lecon/<slug:slug>/terminer/", views.mark_lesson_completed, name="lesson_complete"),
]
