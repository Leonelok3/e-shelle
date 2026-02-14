

#################################################partie recu des utilisateurs ############################################################
 #########################################

from django.db import models
from django.utils import timezone
import uuid


class Receipt(models.Model):
    STATUS_CHOICES = [
        ("paid", "Payé"),
        ("pending", "En attente"),
        ("failed", "Échoué"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt_number = models.CharField(max_length=32, unique=True, blank=True)

    client_full_name = models.CharField(max_length=200)
    client_email = models.EmailField(blank=True, null=True)
    client_phone = models.CharField(max_length=40, blank=True, null=True)

    service_name = models.CharField(max_length=255)
    service_description = models.TextField(blank=True, null=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="XAF")

    payment_method = models.CharField(max_length=64, blank=True, null=True)  # Orange Money, MTN, CB...
    transaction_id = models.CharField(max_length=128, blank=True, null=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="paid")

    issued_at = models.DateTimeField(default=timezone.now)

    # Optionnel : stocker le PDF généré dans MEDIA
    pdf_file = models.FileField(upload_to="receipts/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.receipt_number} - {self.client_full_name}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Ex: IMM97-20260127-AB12
            stamp = timezone.now().strftime("%Y%m%d")
            short = str(uuid.uuid4()).split("-")[0].upper()
            self.receipt_number = f"IMM97-{stamp}-{short}"
        super().save(*args, **kwargs)
