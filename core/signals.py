"""
Signaux du module core pour le partage automatique vers Facebook.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger("facebook_agent")


def setup_facebook_auto_share_signals():
    """Fonction d'enregistrement manuel si nécessaire."""
    from business.models import BusinessProfile
    from core.services.facebook_auto_share import should_share, trigger_async_share_premium

    @receiver(post_save, sender=BusinessProfile, dispatch_uid="core_auto_share_premium_facebook")
    def auto_share_premium(sender, instance, created, **kwargs):
        if instance.is_premium and instance.is_published:
            if should_share(instance):
                trigger_async_share_premium(instance.pk)
