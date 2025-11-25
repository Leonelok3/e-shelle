from django.contrib import admin
from .models import (
    EnglishTest,
    EnglishQuestion,
    UserTestSession,
    UserAnswer,
    EnglishUserProfile,
    EnglishLesson,
    EnglishExercise,
)


# =========================
#  QUESTIONS INLINE
# =========================

class EnglishQuestionInline(admin.TabularInline):
    model = EnglishQuestion
    extra = 3
    fields = ("skill", "question_text", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation")
    show_change_link = True


@admin.register(EnglishTest)
class EnglishTestAdmin(admin.ModelAdmin):
    list_display = ("name", "exam_type", "level", "duration_minutes", "is_active")
    list_filter = ("exam_type", "level", "is_active")
    search_fields = ("name", "description")
    ordering = ("exam_type", "level", "name")
    inlines = [EnglishQuestionInline]


@admin.register(EnglishQuestion)
class EnglishQuestionAdmin(admin.ModelAdmin):
    def short_question(self, obj):
        text = obj.question_text
        return (text[:70] + "…") if len(text) > 70 else text
    short_question.short_description = "Question"

    list_display = ("test", "skill", "short_question", "correct_option")
    list_filter = ("skill", "test__exam_type", "test__level")
    search_fields = ("question_text",)
    autocomplete_fields = ("test",)


# =========================
#  SESSIONS & RÉPONSES
# =========================

@admin.register(UserTestSession)
class UserTestSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "test",
        "score",
        "correct_answers",
        "total_questions",
        "started_at",
        "finished_at",
    )
    list_filter = ("test__exam_type", "test__level", "started_at")
    search_fields = ("user__username", "user__email", "test__name")
    date_hierarchy = "started_at"
    autocomplete_fields = ("user", "test")
    readonly_fields = ("score", "total_questions", "correct_answers", "started_at", "finished_at")


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "selected_option", "is_correct")
    list_filter = ("is_correct", "question__skill", "session__test__exam_type")
    search_fields = ("session__user__username", "question__question_text")
    autocomplete_fields = ("session", "question")


@admin.register(EnglishUserProfile)
class EnglishUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "xp", "total_tests", "best_score")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("xp", "level", "total_tests", "best_score", "badges")


class EnglishExerciseInline(admin.TabularInline):
    model = EnglishExercise
    extra = 1
    fields = ("title", "difficulty", "order", "external_url")


@admin.register(EnglishLesson)
class EnglishLessonAdmin(admin.ModelAdmin):
    list_display = ("title", "test", "skill", "goal", "level", "order")
    list_filter = ("skill", "goal", "level", "test__exam_type")
    search_fields = ("title", "short_description", "content")
    autocomplete_fields = ("test",)
    ordering = ("skill", "order", "title")
    inlines = [EnglishExerciseInline]


@admin.register(EnglishExercise)
class EnglishExerciseAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "difficulty", "order")
    list_filter = ("difficulty", "lesson__skill")
    search_fields = ("title", "description", "content")
    autocomplete_fields = ("lesson",)
    ordering = ("lesson", "order", "title")
