import uuid
from django.db import models


class OCRJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default="queued")
    files = models.JSONField(default=list)
    numbers = models.JSONField(default=list)
    text = models.TextField(blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
