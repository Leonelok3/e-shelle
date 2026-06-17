from django.contrib import admin

from .models import MusicTrackJob, VoiceOverJob, VoiceProfile


@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "consent_confirmed", "is_active", "created_at")
    list_filter = ("consent_confirmed", "is_active", "created_at")
    search_fields = ("name", "owner__username", "consent_note", "provider_voice_id")


@admin.register(VoiceOverJob)
class VoiceOverJobAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "voice_profile", "mode", "status", "duration_seconds", "created_at")
    list_filter = ("mode", "status", "created_at")
    search_fields = ("title", "script", "user__username")
    readonly_fields = ("created_at",)


@admin.register(MusicTrackJob)
class MusicTrackJobAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "mood", "duration_seconds", "status", "created_at")
    list_filter = ("mood", "status", "created_at")
    search_fields = ("title", "prompt", "user__username")
    readonly_fields = ("created_at",)
