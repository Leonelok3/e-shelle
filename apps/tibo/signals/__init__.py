from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tibo.models import Inventory, Product


@receiver(post_save, sender=Product)
def ensure_inventory(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.get_or_create(product=instance)

