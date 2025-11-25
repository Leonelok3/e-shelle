from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='auth.User')
def create_english_profile(sender, instance, created, **kwargs):
    if created:
        # Import à l'intérieur de la fonction pour éviter le problème
        from .models import EnglishUserProfile
        EnglishUserProfile.objects.create(user=instance)

@receiver(post_save, sender='auth.User')
def save_english_profile(sender, instance, **kwargs):
    instance.english_profile.save()
