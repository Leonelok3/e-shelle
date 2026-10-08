from django.apps import AppConfig


class WhatsappCommerceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "whatsapp_commerce"
    verbose_name = "WhatsApp Commerce"

    def ready(self):
        from . import signals  # noqa: F401
