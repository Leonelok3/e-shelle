from django.conf import settings
from django.db import models


class NotificationChannel(models.TextChoices):
    SMS = "SMS", "SMS"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    EMAIL = "EMAIL", "Email"


class NotificationStatus(models.TextChoices):
    QUEUED = "QUEUED", "En file"
    ENVOYEE = "ENVOYEE", "Envoyee"
    SENT = "SENT", "Envoyee"
    FAILED = "FAILED", "Echouee"
    ECHEC = "ECHEC", "Echec"


class NotificationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tchaslucpay_notifications")
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices, db_index=True)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=180, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.QUEUED, db_index=True)
    provider_reference = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Journal notification"
        verbose_name_plural = "Journal notifications"

    def __str__(self):
        return f"{self.channel} -> {self.recipient} ({self.status})"
