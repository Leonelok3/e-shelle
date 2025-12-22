from django.contrib import admin
from django import forms

from .models import (
    Exam, ExamSection, Passage, Asset,
    Question, Choice, Explanation,
    Session, Attempt, Answer,
    CourseLesson, CourseExercise,
)

# =====================================================
# EXAM
# =====================================================

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "language")
    search_fields = ("name", "code")


@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ("exam", "code", "order", "duration_sec")
    list_filter = ("exam", "code")


# =====================================================
# CONTENT
# =====================================================

@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title", "text")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("kind", "file", "lang", "created_at")


# =====================================================
# QUESTIONS
# =====================================================

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "section", "subtype", "difficulty")
    list_filter = ("section", "subtype")
    search_fields = ("stem",)
    inlines = [ChoiceInline]


@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    list_display = ("question",)


# =====================================================
# SESSIONS
# =====================================================

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exam", "mode", "started_at", "completed_at")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "section", "raw_score", "total_items")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "is_correct")


# =====================================================
# COURSE LESSONS (🔥 ICI LA CORRECTION)
# =====================================================

class CourseLessonAdminForm(forms.ModelForm):
    class Meta:
        model = CourseLesson
        fields = "__all__"  # 🔥 FORCE l’affichage de level


class CourseExerciseInline(admin.TabularInline):
    model = CourseExercise
    extra = 1


@admin.register(CourseLesson)
class CourseLessonAdmin(admin.ModelAdmin):
    form = CourseLessonAdminForm

    list_display = (
        "title",
        "exam",
        "section",
        "level",
        "order",
        "is_published",
    )

    list_filter = ("exam", "section", "level", "locale", "is_published")
    ordering = ("order", "id")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CourseExerciseInline]
