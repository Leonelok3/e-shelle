from django.db import models
from stories.models import StoryProject


class Scene(models.Model):
    project = models.ForeignKey(StoryProject, on_delete=models.CASCADE, related_name='scenes')
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=220)
    description = models.TextField()
    narration = models.TextField()
    image_prompt = models.TextField(blank=True)
    duration_seconds = models.FloatField(default=6.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = [('project', 'order')]

    def __str__(self) -> str:
        return f'{self.project_id} - Scène {self.order}: {self.title}'
