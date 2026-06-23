from django.contrib import admin
from .models import StoryProject


@admin.register(StoryProject)
class StoryProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'progress', 'created_at')
    search_fields = ('title', 'prompt', 'story_text')
    list_filter = ('status', 'created_at')
