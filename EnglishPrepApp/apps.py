from django.apps import AppConfig

# Import des signaux à un niveau global
from .signals import *  # Import explicite des signaux

class EnglishprepappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'EnglishPrepApp'

    def ready(self):
        # La fonction ready n'a plus besoin de l'import ici
        pass
