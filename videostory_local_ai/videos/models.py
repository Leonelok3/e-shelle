from django.db import models
from stories.models import StoryProject


class VideoRender(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'En cours'
        DONE = 'done', 'Terminé'
        FAILED = 'failed', 'Échec'

    project = models.ForeignKey(StoryProject, on_delete=models.CASCADE, related_name='renders')
    video = models.FileField(upload_to='generated/videos/', blank=True, null=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.RUNNING)
    log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Render projet {self.project_id} - {self.status}'


class RenderJob(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        RUNNING = 'running', 'En cours'
        DONE = 'done', 'Terminé'
        FAILED = 'failed', 'Échec'

    project = models.ForeignKey(StoryProject, on_delete=models.CASCADE, related_name='render_jobs')
    job_type = models.CharField(max_length=50, default='avatar')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Job {self.pk} ({self.job_type}) - {self.status}'
