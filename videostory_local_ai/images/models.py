from django.db import models
from scenes.models import Scene


class GeneratedImage(models.Model):
    scene = models.OneToOneField(Scene, on_delete=models.CASCADE, related_name='generated_image')
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True)
    image = models.ImageField(upload_to='generated/images/', blank=True, null=True)
    seed = models.BigIntegerField(null=True, blank=True)
    backend = models.CharField(max_length=80, default='comfyui')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Image scène {self.scene_id}'
