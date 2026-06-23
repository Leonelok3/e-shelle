from django.contrib import admin
from .models import AdProject, VoiceTrack, VideoProject


@admin.register(AdProject)
class AdProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'created_at')


@admin.register(VoiceTrack)
class VoiceTrackAdmin(admin.ModelAdmin):
    list_display = ('project', 'backend', 'language')


@admin.register(VideoProject)
class VideoProjectAdmin(admin.ModelAdmin):
    list_display = ('project', 'resolution', 'aspect')
