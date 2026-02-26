from django.contrib import admin
from django import forms
from django.utils.html import format_html

from .models import (
    Exam, ExamSection, Passage, Asset,
    Question, Choice, Explanation,
    Session, Attempt, Answer,
    CourseLesson, CourseExercise,
    EOSubmission, EESubmission,
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
    list_display = ("id", "kind", "lang", "file_preview", "created_at")
    list_filter = ("kind", "lang")

    def file_preview(self, obj):
        if obj.file and obj.kind == "audio":
            return format_html(
                '<audio controls style="height:30px;"><source src="{}"></audio>',
                obj.file.url
            )
        elif obj.file:
            return obj.file.name
        return "—"
    file_preview.short_description = "Fichier"


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
# COURSE EXERCISES — formulaire avec upload audio direct
# =====================================================

class CourseExerciseForm(forms.ModelForm):
    """
    Permet d'uploader un fichier audio directement depuis l'inline
    sans avoir à créer un Asset séparément.
    """
    audio_upload = forms.FileField(
        required=False,
        label="Uploader un audio (MP3/OGG)",
        help_text="Laisse vide pour garder l'audio existant. Sélectionne un fichier pour en uploader un nouveau.",
        widget=forms.FileInput(attrs={"accept": "audio/*"}),
    )

    class Meta:
        model = CourseExercise
        fields = "__all__"

    def save(self, commit=True):
        instance = super().save(commit=False)
        audio_file = self.cleaned_data.get("audio_upload")

        if audio_file:
            # Créer un nouvel Asset audio automatiquement
            asset = Asset(kind="audio", lang="fr")
            asset.file.save(audio_file.name, audio_file, save=True)
            instance.audio = asset

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class CourseExerciseInline(admin.TabularInline):
    model = CourseExercise
    form = CourseExerciseForm
    extra = 1
    fields = (
        "order", "title", "instruction", "question_text",
        "audio", "audio_upload",
        "option_a", "option_b", "option_c", "option_d",
        "correct_option", "summary", "is_active",
    )


# =====================================================
# COURSE LESSONS
# =====================================================

class CourseLessonAdminForm(forms.ModelForm):
    class Meta:
        model = CourseLesson
        fields = "__all__"


@admin.register(CourseLesson)
class CourseLessonAdmin(admin.ModelAdmin):
    form = CourseLessonAdminForm

    list_display = (
        "title",
        "get_exams",
        "section",
        "level",
        "order",
        "is_published",
    )

    list_filter = ("section", "level", "locale", "is_published")
    search_fields = ("title", "slug")
    ordering = ("level", "order", "id")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CourseExerciseInline]

    def get_exams(self, obj):
        return ", ".join(e.code.upper() for e in obj.exams.all())
    get_exams.short_description = "Examens"


# =====================================================
# COURSE EXERCISE (vue standalone)
# =====================================================

@admin.register(CourseExercise)
class CourseExerciseAdmin(admin.ModelAdmin):
    form = CourseExerciseForm
    list_display = ("id", "lesson", "order", "title", "correct_option", "has_audio", "is_active")
    list_filter = ("is_active", "lesson__section", "lesson__level")
    search_fields = ("title", "question_text")
    ordering = ("lesson", "order")

    def has_audio(self, obj):
        return bool(obj.audio)
    has_audio.boolean = True
    has_audio.short_description = "Audio"


# =====================================================
# SOUMISSIONS EO / EE
# =====================================================

@admin.register(EOSubmission)
class EOSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exercise", "score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "transcript")
    readonly_fields = ("transcript", "feedback_json", "created_at")
    ordering = ("-created_at",)


@admin.register(EESubmission)
class EESubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exercise", "word_count", "score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "text")
    readonly_fields = ("feedback_json", "created_at")
    ordering = ("-created_at",)
