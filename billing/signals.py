# billing/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Transaction
from .services_affiliate import create_commission_for_transaction


@receiver(post_save, sender=Transaction)
def create_commission_on_transaction_completed(sender, instance: Transaction, created, **kwargs):
    # On tente à chaque save, mais la contrainte unique empêche les doublons
    if instance.status == "COMPLETED":
        create_commission_for_transaction(instance)
