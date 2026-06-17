from django.urls import path

from . import views

app_name = "audio_studio"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("voices/new/", views.VoiceProfileCreateView.as_view(), name="voice_create"),
    path("voiceovers/new/", views.VoiceOverCreateView.as_view(), name="voiceover_create"),
    path("music/new/", views.MusicTrackCreateView.as_view(), name="music_create"),
]
