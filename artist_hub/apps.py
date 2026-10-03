from django.apps import AppConfig


class ArtistHubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "artist_hub"
    verbose_name = "Artist Hub (Group Opus)"

    def ready(self):
        # Enregistrement des récepteurs de signaux
        try:
            import artist_hub.casting.signals  # noqa: F401
        except ImportError:
            pass
