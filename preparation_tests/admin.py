from django.contrib import admin
from .models import (
    Exam, ExamSection, Passage, Asset,
    Question, Choice, Explanation,
    Session, Attempt, Answer,
    CourseLesson, CourseExercise,
)


# ----------- Admin pour Exam -----------

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "language")
    search_fields = ("name", "code")


# ----------- Admin pour ExamSection -----------

@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ("exam", "code", "order", "duration_sec")
    list_filter = ("exam", "code")


# ----------- Admin pour Passage -----------

@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title", "text")


# ----------- Admin pour Asset -----------

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("kind", "url", "lang")
    list_filter = ("kind", "lang")
    search_fields = ("url",)


# ----------- Inline pour les Choices -----------

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1


# ----------- Admin pour Question -----------

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "section", "subtype", "difficulty")
    list_filter = ("section", "subtype")
    search_fields = ("stem",)
    inlines = [ChoiceInline]


# ----------- Admin pour Explanation -----------

@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    list_display = ("question",)


# ----------- Admin pour Session -----------

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exam", "mode", "started_at", "completed_at")
    list_filter = ("exam", "mode")


# ----------- Admin pour Attempt -----------

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "section", "raw_score", "total_items")


# ----------- Admin pour Answer -----------

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "is_correct")
    list_filter = ("is_correct", "attempt__session__exam")


# ----------- Inline + Admin pour CourseLesson / CourseExercise -----------

class CourseExerciseInline(admin.TabularInline):
    model = CourseExercise
    extra = 1
    fields = (
        "title",
        "instruction",
        "question_text",
        "audio",
        "image",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "summary",
        "order",
        "is_active",
    )
    ordering = ("order", "id")


@admin.register(CourseLesson)
class CourseLessonAdmin(admin.ModelAdmin):
    list_display = ("title", "exam", "section", "locale", "order", "is_published", "updated_at")
    list_filter = ("exam", "section", "locale", "is_published")
    search_fields = ("title", "slug", "content_html")
    ordering = ("exam", "section", "order", "id")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CourseExerciseInline]
