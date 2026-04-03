from django.apps import AppConfig


class EduPlatformConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'edu_platform'
    verbose_name = 'EduCam Pro — Plateforme E-Learning'

    def ready(self):
        import edu_platform.signals  # noqa: F401
