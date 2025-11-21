from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProgress

User = get_user_model()

@receiver(post_save, sender=User)
def create_progress(sender, instance, created, **kwargs):
    if created:
        UserProgress.objects.create(user=instance)
