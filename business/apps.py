from django.apps import AppConfig


class BusinessConfig(AppConfig):
    name = 'business'

    def ready(self):
        import business.signals  # noqa
