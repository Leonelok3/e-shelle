"""
artist_hub/payments/signals.py
Signaux émis lors des transitions d'état des paiements.
Permet un découplage total entre le paiement et les modules métier (casting, billetterie, etc.).
"""
from django.dispatch import Signal

# Émis lorsqu'un paiement est validé avec succès (par webhook, verify serveur ou admin)
# Arguments fournis : payment, target_object, raw_data
payment_succeeded = Signal()

# Émis lorsqu'un paiement échoue
payment_failed = Signal()

# Émis lorsqu'un paiement est annulé ou expiré
payment_cancelled = Signal()
