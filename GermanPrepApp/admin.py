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
    GermanCompetencyTag,
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
    list_display = ("id", "lesson", "question_text_short", "correct_option")
    search_fields = ("question_text",)
    list_filter = ("lesson__exam__level", "lesson__skill")
    filter_horizontal = ("competency_tags",)

    def question_text_short(self, obj):
        return obj.question_text[:60] + "…" if len(obj.question_text) > 60 else obj.question_text
    question_text_short.short_description = "Question"


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


# =====================================================
# 🎯 TAGS DE COMPÉTENCE GRANULAIRES (Goethe)
# =====================================================

@admin.register(GermanCompetencyTag)
class GermanCompetencyTagAdmin(admin.ModelAdmin):
    list_display  = ("label", "skill", "exercises_count")
    list_filter   = ("skill",)
    search_fields = ("label", "description")
    ordering      = ("skill", "label")

    def exercises_count(self, obj):
        return obj.exercises.count()
    exercises_count.short_description = "Exercices liés"
