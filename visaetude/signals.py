from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import VisaProgress

User = get_user_model()


@receiver(post_save, sender=User)
def create_visa_progress(sender, instance, created, **kwargs):
    """
    Crée automatiquement la progression Visa Études
    pour chaque nouvel utilisateur.
    """
    if created:
        VisaProgress.objects.create(user=instance)
