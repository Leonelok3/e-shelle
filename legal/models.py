from django.db import models
from django.utils import timezone

class ProtectionProtocol(models.Model):
    title = models.CharField(
        max_length=255,
        default="Protocole de protection Immigration97"
    )

    content = models.TextField(
        help_text="Texte juridique officiel du protocole"
    )

    is_active = models.BooleanField(default=True)

    version = models.CharField(
        max_length=20,
        default="v1.0"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Protocole de protection"
        verbose_name_plural = "Protocoles de protection"

    def __str__(self):
        return f"{self.title} ({self.version})"
