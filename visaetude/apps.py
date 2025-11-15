# visaetude/apps.py
from django.apps import AppConfig

class VisaetudeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "visaetude"

    def ready(self):
        from . import signals  # noqa
