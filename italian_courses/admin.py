# italian_courses/admin.py
from django.contrib import admin

from .models import (
    CourseCategory,
    Lesson,
    LessonProgress,
    Quiz,
    Question,
    Choice,
)

# Si tu as un LessonAdminForm, il doit exister réellement.
# Sinon, commente la ligne ci-dessous et l'attribut form dans LessonAdmin.
try:
    from .forms import LessonAdminForm
except Exception:
    LessonAdminForm = None


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2
    fields = ("order", "text", "is_correct")
    ordering = ("order", "id")


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    show_change_link = True
    fields = ("order", "prompt", "explanation")
    ordering = ("order", "id")


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("lesson", "title", "is_active", "order", "created_at")
    list_filter = ("is_active", "lesson__category")
    search_fields = ("lesson__title", "title", "lesson__category__name")
    ordering = ("lesson", "order", "title")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "short_prompt")
    list_filter = ("quiz",)
    search_fields = ("quiz__title", "prompt")
    ordering = ("quiz", "order", "id")
    inlines = [ChoiceInline]

    @admin.display(description="Prompt")
    def short_prompt(self, obj: Question) -> str:
        text = (obj.prompt or "").strip()
        return text[:80] + ("…" if len(text) > 80 else "")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    form = LessonAdminForm if LessonAdminForm else None

    list_display = (
        "title",
        "category",
        "is_published",
        "order",
        "has_audio",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_published", "category")
    search_fields = ("title", "slug", "category__name")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("category", "order", "title")

    fieldsets = (
        (None, {"fields": ("category", "title", "slug", "is_published", "order", "estimated_minutes")}),
        ("Content", {"fields": ("content_html", "transcript")}),
        ("Audio", {"fields": ("audio_file",)}),
        ("Dates", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at", "updated_at")

    @admin.display(boolean=True, description="Audio")
    def has_audio(self, obj: Lesson) -> bool:
        return bool(obj.audio_file)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "lesson",
        "completed",
        "progress_percent",
        "last_accessed_at",
        "completed_at",
    )
    list_filter = ("completed", "last_accessed_at")
    search_fields = ("user__username", "user__email", "lesson__title")
    readonly_fields = ("started_at", "last_accessed_at")

    fieldsets = (
        (None, {"fields": ("user", "lesson")}),
        ("Progress", {"fields": ("progress_percent", "completed", "last_position_seconds")}),
        ("Dates", {"fields": ("started_at", "last_accessed_at", "completed_at")}),
    )


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "text", "is_correct")
    list_filter = ("is_correct",)
    search_fields = ("question__prompt", "text")
    ordering = ("question", "order", "id")
