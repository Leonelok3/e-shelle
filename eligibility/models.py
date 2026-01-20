from django.conf import settings
from django.db import models


class Session(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="eligibility_sessions"
    )
    locale = models.CharField(max_length=8, default="fr")
    source = models.CharField(max_length=32, default="wizard")

    answers_json = models.JSONField(default=dict, blank=True)
    result_json = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Eligibility Session"
        verbose_name_plural = "Eligibility Sessions"

    def __str__(self):
        return f"EligibilitySession#{self.id} ({self.user_id})"
