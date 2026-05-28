from django.apps import AppConfig


class TiboConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tibo"
    label = "tibo"
    verbose_name = "TIBO Dropshipping"

    def ready(self):
        from . import signals  # noqa: F401

