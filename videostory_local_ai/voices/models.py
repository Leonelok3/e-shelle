from django.db import models
from scenes.models import Scene


class VoiceOver(models.Model):
    scene = models.OneToOneField(Scene, on_delete=models.CASCADE, related_name='voice_over')
    text = models.TextField()
    audio = models.FileField(upload_to='generated/audio/', blank=True, null=True)
    backend = models.CharField(max_length=80, default='coqui')
    duration_seconds = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Voix scène {self.scene_id}'


class ClonedVoice(models.Model):
    name = models.CharField(max_length=120)
    voice_file = models.FileField(upload_to='cloned_voices/', blank=True, null=True)
    voice_id = models.CharField(max_length=120, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

