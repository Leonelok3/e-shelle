from django.contrib import admin
from .models import Letter

@admin.register(Letter)
class LetterAdmin(admin.ModelAdmin):
    list_display = ("full_name", "target_role", "company", "language", "tone", "ats_score", "source", "created_at")
    search_fields = ("full_name", "target_role", "company", "content")
    list_filter = ("language", "tone", "source", "created_at")
