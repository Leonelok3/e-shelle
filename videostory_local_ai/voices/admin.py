from django.contrib import admin
from .models import VoiceOver


@admin.register(VoiceOver)
class VoiceOverAdmin(admin.ModelAdmin):
    list_display = ('id', 'scene', 'backend', 'duration_seconds', 'created_at')
