from django.db import models

class TranslationJob(models.Model):
    original_name = models.CharField(max_length=255, blank=True)
    source_lang = models.CharField(max_length=10, blank=True, default="auto")
    target_lang = models.CharField(max_length=10, blank=True, default="en")

    original_file = models.FileField(upload_to="documents/translation/original/")
    translated_file = models.FileField(upload_to="documents/translation/translated/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_name or 'Document'} ({self.source_lang}->{self.target_lang})"
