"""
Enregistrement des modèles dans l'admin Django pour faciliter la création de données.
"""
from django.contrib import admin
from .models import Exam, ExamSection, Passage, Asset, Question, Choice, Explanation, Session, Attempt, Answer

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "language")
    search_fields = ("code", "name")

@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ("exam", "code", "order", "duration_sec")
    list_filter = ("exam", "code")
    ordering = ("exam", "order")

@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title", "text")

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("kind", "url", "lang")
    list_filter = ("kind", "lang")
    search_fields = ("url",)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "section", "subtype", "difficulty")
    list_filter = ("section__exam", "section__code", "subtype")
    search_fields = ("stem",)
    inlines = [ChoiceInline]

@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    list_display = ("question",)
    # >>> ajout immigration97 (sûr) : recherche plein-texte sur l’explication
    search_fields = ("text_md",)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exam", "mode", "started_at", "completed_at")
    list_filter = ("exam", "mode")

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "section", "raw_score", "total_items", "elapsed_sec")

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "is_correct", "submitted_at")
    list_filter = ("is_correct",)
