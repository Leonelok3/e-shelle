from django.contrib import admin
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


@admin.register(GermanExam)
class GermanExamAdmin(admin.ModelAdmin):
    list_display = ("title", "exam_type", "level", "is_active")
    list_filter = ("exam_type", "level", "is_active")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(GermanLesson)
class GermanLessonAdmin(admin.ModelAdmin):
    list_display = ("title", "exam", "skill", "order")
    list_filter = ("exam", "skill")
    search_fields = ("title", "intro", "content")


@admin.register(GermanExercise)
class GermanExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "question_text")
    search_fields = ("question_text",)


@admin.register(GermanResource)
class GermanResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "resource_type", "exam", "lesson")
    list_filter = ("resource_type", "exam")
    search_fields = ("title", "description", "url")


@admin.register(GermanPlacementQuestion)
class GermanPlacementQuestionAdmin(admin.ModelAdmin):
    list_display = ("order", "question_text", "is_active")
    list_filter = ("is_active",)
    search_fields = ("question_text",)


@admin.register(GermanTestSession)
class GermanTestSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exam", "score", "started_at", "finished_at")
    list_filter = ("exam", "started_at")


@admin.register(GermanUserAnswer)
class GermanUserAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "exercise", "selected_option", "is_correct")


@admin.register(GermanUserProfile)
class GermanUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "xp", "level", "total_tests", "best_score", "placement_level", "placement_score")
