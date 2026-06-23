from django.db import models


class StoryProject(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        RUNNING = 'running', 'Génération en cours'
        DONE = 'done', 'Terminé'
        FAILED = 'failed', 'Échec'

    title = models.CharField(max_length=220, blank=True)
    prompt = models.TextField(blank=True)
    story_text = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    progress = models.PositiveSmallIntegerField(default=0)
    current_step = models.CharField(max_length=160, blank=True)
    error_message = models.TextField(blank=True)
    final_video = models.FileField(upload_to='generated/videos/', blank=True, null=True)
    
    # Talking Avatar fields
    is_avatar_project = models.BooleanField(default=False)
    avatar_image = models.ImageField(upload_to='avatars/', blank=True, null=True)
    script_text = models.TextField(blank=True)
    avatar_background = models.CharField(max_length=100, default='office', blank=True)
    cloned_voice = models.ForeignKey('voices.ClonedVoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title or f'Projet #{self.pk}'

    def mark_progress(self, step: str, progress: int) -> None:
        self.current_step = step
        self.progress = max(0, min(100, progress))
        self.save(update_fields=['current_step', 'progress', 'updated_at'])

