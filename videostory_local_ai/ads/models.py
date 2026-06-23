from django.db import models
from businesses.models import Business


class AdProject(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='ad_projects')
    title = models.CharField(max_length=220, blank=True)
    duration_seconds = models.PositiveIntegerField(default=30)
    status = models.CharField(max_length=30, default='draft')
    final_video = models.FileField(upload_to='generated/videos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title or f'AdProject {self.pk}'


class VoiceTrack(models.Model):
    project = models.ForeignKey(AdProject, on_delete=models.CASCADE, related_name='voice_tracks')
    backend = models.CharField(max_length=80, default='coqui')
    audio = models.FileField(upload_to='generated/audio/', blank=True, null=True)
    language = models.CharField(max_length=20, default='fr')
    created_at = models.DateTimeField(auto_now_add=True)


class VideoProject(models.Model):
    project = models.ForeignKey(AdProject, on_delete=models.CASCADE, related_name='video_projects')
    resolution = models.CharField(max_length=20, default='1080x1920')
    aspect = models.CharField(max_length=20, default='vertical')
    created_at = models.DateTimeField(auto_now_add=True)
